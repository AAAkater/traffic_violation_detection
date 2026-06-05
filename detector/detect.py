"""检测流水线 — 编排检测、空间过滤、画框保存全流程。

图片预处理（象限分割）由 preprocess.py 独立完成，本模块直接读取
预处理后的 cropped/ 子目录，不再执行分割操作。

检测后在象限图上画框，保存到 tags/ 目录，供 LLM 判定使用。
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field
from tqdm import tqdm

from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.utils import logger

# 预处理输出的象限文件名 → 中文象限名
QUADRANT_NAME_MAP: dict[str, str] = {
    "topleft": "左上",
    "topright": "右上",
    "bottomleft": "左下",
}

# 中文象限名 → 预处理文件名（反向映射）
QUADRANT_NAME_RMAP: dict[str, str] = {v: k for k, v in QUADRANT_NAME_MAP.items()}

# 检测顺序
DETECT_ORDER: list[str] = ["左上", "右上", "左下"]


class DetectionStats(BaseModel):
    """单张图片的检测统计结果。"""

    all: int = Field(default=0, description="YOLO 原始检出总数")
    vehicle: int = Field(default=0, description="正面机动车灯数量")


def _load_quadrants(
    sample_dir: Path,
) -> list[tuple[str, np.ndarray]]:
    """从 cropped/ 子目录加载象限图片。"""
    cropped_dir = sample_dir / "cropped"
    if not cropped_dir.is_dir():
        raise FileNotFoundError(f"缺少 cropped/ 目录: {cropped_dir}")

    quadrants: list[tuple[str, np.ndarray]] = []
    for eng_name, cn_name in QUADRANT_NAME_MAP.items():
        for ext in (".jpg", ".jpeg", ".png", ".bmp"):
            q_path = cropped_dir / f"{eng_name}{ext}"
            if q_path.exists():
                img = cv2.imread(str(q_path))
                if img is not None:
                    quadrants.append((cn_name, img))
                    break
        else:
            logger.warning(f"缺少象限图: {cropped_dir / eng_name}")

    return quadrants


def run(
    sample_dir: str,
    model_path: str,
    conf_threshold: float = 0.5,
) -> DetectionStats:
    """对预处理后的样本目录执行红绿灯检测流水线。"""
    detector = TrafficLightDetector(model_path, conf_threshold=conf_threshold)
    sample_path = Path(sample_dir)
    image_stem = sample_path.name

    quadrants = _load_quadrants(sample_path)
    if not quadrants:
        logger.warning(f"[{image_stem}] 未找到任何象限图，跳过")
        return DetectionStats()

    stats = DetectionStats()

    # 对每个象限独立检测
    per_quadrant_detections: dict[str, list[Detection]] = {}

    for q_name, q_img in quadrants:
        if q_name not in DETECT_ORDER:
            continue

        logger.debug(f"[{image_stem}][{q_name}] 检测中…")
        raw = detector.detect(q_img)

        if not raw:
            logger.debug(f"[{image_stem}][{q_name}] 检出 0 个")
            per_quadrant_detections[q_name] = []
            continue

        h, w = q_img.shape[:2]
        logger.debug(
            f"[{image_stem}][{q_name}] YOLO检出 {len(raw)} 个: "
            + ", ".join(
                f"({d.width:.0f}×{d.height:.0f}@{d.confidence:.2f})" for d in raw
            )
        )

        vehicle = detector.filter_spatial(
            raw,
            image_height=h,
            image_width=w,
            label=f"[{image_stem}][{q_name}]",
        )
        per_quadrant_detections[q_name] = vehicle
        stats.all += len(raw)
        stats.vehicle += len(vehicle)

        if vehicle:
            logger.debug(
                f"[{image_stem}][{q_name}] 检出成功, "
                f"all={len(raw)} vehicle={len(vehicle)}"
            )
        else:
            logger.debug(f"[{image_stem}][{q_name}] 未检出")

    # 在象限图上画检测框，保存到 tags/
    tags_out_dir = sample_path / "tags"
    tags_out_dir.mkdir(parents=True, exist_ok=True)

    for name, sub_img in quadrants:
        if name not in DETECT_ORDER:
            continue

        eng_name = QUADRANT_NAME_RMAP[name]
        detections = per_quadrant_detections.get(name, [])

        sub_img_rgb = cv2.cvtColor(sub_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(sub_img_rgb)

        annotated = (
            detector.draw_detections(pil_img, detections) if detections else pil_img
        )
        annotated.save(str(tags_out_dir / f"{eng_name}_det.jpg"), quality=95)
        logger.debug(
            f"[{image_stem}][{name}] 保存标注图: {tags_out_dir / f'{eng_name}_det.jpg'}"
        )

    return stats


def run_batch(
    preprocessed_dir: str,
    model_path: str,
    conf_threshold: float = 0.5,
) -> None:
    """对预处理后的目录批量执行红绿灯检测。

    预处理目录由 preprocess.py 生成，结构如下：
        preprocessed_dir/
        ├── 710710/
        │   ├── 710710.jpg
        │   ├── cropped/
        │   │   ├── topleft.jpg
        │   │   ├── topright.jpg
        │   │   └── bottomleft.jpg
        │   └── tags/
        │       └── bottomright.jpg
        ├── 1013006/
        │   └── ...
        └── ...

    Args:
        preprocessed_dir: 预处理后的输出根目录（由 preprocess.py 生成）。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
    """
    base_path = Path(preprocessed_dir)
    if not base_path.is_dir():
        logger.error(f"文件夹不存在: {preprocessed_dir}")
        return

    # 筛选包含 cropped/ 子目录的样本目录
    sample_dirs = sorted(
        d for d in base_path.iterdir() if d.is_dir() and (d / "cropped").is_dir()
    )

    if not sample_dirs:
        logger.warning(f"未找到包含 cropped/ 的样本目录: {preprocessed_dir}")
        return

    total = len(sample_dirs)
    logger.info(f"=== 批量检测开始，共 {total} 个样本，目录: {preprocessed_dir} ===")

    total_all = 0
    total_vehicle = 0
    total_skipped = 0

    # 进度条：只显示文件名和关键统计
    pbar = tqdm(sample_dirs, desc="检测", unit="img", ncols=100)

    for sample_dir in pbar:
        stem = sample_dir.name
        stats = run(
            sample_dir=str(sample_dir),
            model_path=model_path,
            conf_threshold=conf_threshold,
        )
        total_all += stats.all
        total_vehicle += stats.vehicle
        if stats.all == 0:
            total_skipped += 1

        # 更新进度条后缀
        pbar.set_postfix_str(f"all={total_all} vehicle={total_vehicle} | {stem}")

    pbar.close()

    # 最终汇总
    summary = (
        f"\n{'=' * 50}\n"
        f"  批量检测完成\n"
        f"  总处理: {total} 个\n"
        f"  总检出: {total_all} 个\n"
        f"  正面机动车灯: {total_vehicle} 个\n"
        f"  无检出: {total_skipped} 个\n"
        f"  结果目录: {preprocessed_dir}\n"
        f"{'=' * 50}"
    )
    print(summary)
    logger.info(summary.replace("\n", " | "))
