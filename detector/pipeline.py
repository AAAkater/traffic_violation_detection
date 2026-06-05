"""检测流水线 — 编排检测、空间过滤、画框保存全流程。

图片预处理（象限分割）由 preprocess.py 独立完成，本模块直接读取
预处理后的 cropped/ 子目录，不再执行分割操作。

检测后在象限图上画框，保存到 tags/ 目录，供 LLM 判定使用。
"""

import shutil
from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel, Field
from tqdm import tqdm

from detector.filter import filter_spatial
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.utils import logger
from detector.utils.image_tools import compress_quadrants_to_1080p

# 预处理输出的象限文件名 → 中文象限名
QUADRANT_NAME_MAP: dict[str, str] = {
    "topleft": "左上",
    "topright": "右上",
    "bottomleft": "左下",
}

# 中文象限名 → 预处理文件名（反向映射）
QUADRANT_NAME_RMAP: dict[str, str] = {v: k for k, v in QUADRANT_NAME_MAP.items()}

# 检测顺序：依次尝试，直到成功检出
DETECT_ORDER: list[str] = ["左上", "右上", "左下"]

# 检测框颜色（BGR）
BOX_COLOR = (0, 255, 0)  # 绿色
BOX_THICKNESS = 3
FONT_SCALE = 0.8
FONT_COLOR = (255, 255, 255)  # 白色
FONT_THICKNESS = 2


class DetectionStats(BaseModel):
    """单张图片的检测统计结果。"""

    all: int = Field(default=0, description="YOLO 原始检出总数")
    vehicle: int = Field(default=0, description="正面机动车灯数量")


def _draw_detections(
    img: np.ndarray,
    detections: list[Detection],
    *,
    color: tuple[int, int, int] = BOX_COLOR,
    thickness: int = BOX_THICKNESS,
    font_scale: float = FONT_SCALE,
    font_color: tuple[int, int, int] = FONT_COLOR,
    font_thickness: int = FONT_THICKNESS,
) -> np.ndarray:
    """在图片上绘制检测框和标签，返回标注后的图片副本。

    Args:
        img: 原始图像（BGR 格式 numpy 数组）。
        detections: 检测结果列表。
        color: 框线颜色 (B, G, R)。
        thickness: 框线粗细。
        font_scale: 字体大小。
        font_color: 字体颜色 (B, G, R)。
        font_thickness: 字体粗细。

    Returns:
        标注后的图片副本（不修改原图）。
    """
    annotated = img.copy()
    for det in detections:
        x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
        label = f"{det.class_name} {det.confidence:.2f}"

        # 画检测框
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

        # 计算标签背景大小
        (tw, th), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
        )
        # 标签背景放在框上方
        label_y = max(y1 - 5, th + 5)
        cv2.rectangle(
            annotated,
            (x1, label_y - th - 5),
            (x1 + tw + 4, label_y + baseline),
            color,
            cv2.FILLED,
        )
        cv2.putText(
            annotated,
            label,
            (x1 + 2, label_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            font_color,
            font_thickness,
        )
    return annotated


def _load_quadrants(
    sample_dir: Path,
) -> list[tuple[str, np.ndarray]]:
    """从预处理目录中加载象限图片。

    预处理目录结构：
        sample_dir/
        ├── cropped/
        │   ├── topleft.jpg
        │   ├── topright.jpg
        │   └── bottomleft.jpg
        └── tags/
            └── bottomright.jpg

    Args:
        sample_dir: 预处理后的样本目录路径。

    Returns:
        [(中文象限名, 图片数组), ...]，仅包含成功加载的象限。
    """
    cropped_dir = sample_dir / "cropped"
    if not cropped_dir.is_dir():
        raise FileNotFoundError(f"缺少 cropped/ 目录: {cropped_dir}")

    quadrants: list[tuple[str, np.ndarray]] = []
    for eng_name, cn_name in QUADRANT_NAME_MAP.items():
        # 支持 .jpg / .png 等常见扩展名
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
    """对预处理后的样本目录执行红绿灯检测流水线。

    调用前需先运行 preprocess.py 生成目录结构：
        sample_dir/
        ├── <原图>.jpg
        ├── cropped/
        │   ├── topleft.jpg
        │   ├── topright.jpg
        │   └── bottomleft.jpg
        └── tags/
            └── bottomright.jpg

    流程：
    1. 从 cropped/ 加载象限图片
    2. 依次在 左上 → 右上 → 左下 上执行 YOLO 检测
    3. 空间过滤
    4. 在象限图上画检测框，保存到 tags/ 目录
    5. 其余象限复用检测 bbox 画框保存

    Args:
        sample_dir: 预处理后的样本目录路径（由 preprocess.py 生成）。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。

    Returns:
        DetectionStats 统计信息。
    """
    detector = TrafficLightDetector(model_path, conf_threshold=conf_threshold)
    sample_path = Path(sample_dir)
    image_stem = sample_path.name

    # 1. 从预处理目录加载象限图片
    quadrants = _load_quadrants(sample_path)
    if not quadrants:
        logger.warning(f"[{image_stem}] 未找到任何象限图，跳过")
        return DetectionStats()

    # 保存象限图到 quadrants/ 目录（供后续判定模块使用）
    quadrants_dir = str(sample_path / "quadrants")
    Path(quadrants_dir).mkdir(parents=True, exist_ok=True)
    for cn_name, q_img in quadrants:
        cv2.imwrite(str(Path(quadrants_dir) / f"quadrant_{cn_name}.jpg"), q_img)

    # 保存右下角（嫌疑车辆图）到 quadrants/ 目录
    tags_dir = sample_path / "tags"
    if tags_dir.is_dir():
        for ext in (".jpg", ".jpeg", ".png", ".bmp"):
            br_path = tags_dir / f"bottomright{ext}"
            if br_path.exists():
                shutil.copy2(br_path, Path(quadrants_dir) / "quadrant_右下.jpg")
                break

    stats = DetectionStats()

    # ------------------------------------------------------------------
    # 2. 依次在 左上 → 右上 → 左下 上执行完整检测流水线，
    #    直到某个象限成功检出为止。
    #    三者为同一摄像头同一角度不同时间的拍照，交通灯位置相同，
    #    检出成功后，其余象限直接复用检测 bbox 画框。
    # ------------------------------------------------------------------

    def _detect_quadrant(
        q_name: str,
        q_img: np.ndarray,
    ) -> tuple[list[Detection], list[Detection]]:
        """对单个象限执行完整管线（YOLO → 空间过滤）。

        直接对整个象限图执行 YOLO 检测，然后只保留中上部分的标签。

        Returns:
            (raw, vehicle): YOLO 原始检出 + 空间过滤后的机动车灯。
        """
        logger.debug(f"[{image_stem}][{q_name}] 检测中…")

        raw = detector.detect(q_img)

        if not raw:
            logger.debug(f"[{image_stem}][{q_name}] 检出 0 个")
            return raw, []

        h, w = q_img.shape[:2]
        _label = f"[{image_stem}][{q_name}]"

        logger.debug(
            f"[{image_stem}][{q_name}] YOLO检出 {len(raw)} 个: "
            + ", ".join(
                f"({d.width:.0f}×{d.height:.0f}@{d.confidence:.2f})" for d in raw
            )
        )

        # 空间过滤：只保留中上部分的检测框
        upper_detections, removed_lower, removed_edge = filter_spatial(
            raw,
            image_height=h,
            image_width=w,
            image=q_img,
            upper_ratio=0.5,
            edge_ratio=0.20,
            label=_label,
        )

        if not upper_detections:
            logger.debug(f"[{image_stem}][{q_name}] 空间过滤后 0 个中上区域框")
            return raw, []

        # 空间过滤后的结果直接作为机动车灯检测结果
        vehicle_detections = upper_detections

        if not vehicle_detections:
            return raw, []

        return raw, vehicle_detections

    # 依次尝试 左上 → 右上 → 左下，直到成功检出
    primary_name: str | None = None
    shared_detections: list[Detection] = []

    for q_name, q_img in quadrants:
        if q_name not in DETECT_ORDER:
            continue  # 跳过非检测象限
        raw, vehicle = _detect_quadrant(q_name, q_img)
        if vehicle:
            primary_name = q_name
            shared_detections = vehicle
            stats.all += len(raw)
            stats.vehicle += len(vehicle)
            logger.debug(
                f"[{image_stem}] 检出成功象限: {q_name}, "
                f"all={len(raw)} vehicle={len(vehicle)}"
            )
            break
        else:
            logger.debug(f"[{image_stem}][{q_name}] 未检出，尝试下一象限")

    # ------------------------------------------------------------------
    # 3. 在象限图上画检测框，保存到 tags/ 目录
    # ------------------------------------------------------------------
    tags_out_dir = sample_path / "tags"
    tags_out_dir.mkdir(parents=True, exist_ok=True)

    for name, sub_img in quadrants:
        if name not in DETECT_ORDER:
            continue  # 右下不同角度，跳过

        eng_name = QUADRANT_NAME_RMAP[name]

        if shared_detections:
            # 在象限图上画检测框
            annotated = _draw_detections(sub_img, shared_detections)
            out_path = tags_out_dir / f"{eng_name}_det.jpg"
            cv2.imwrite(str(out_path), annotated)
            logger.debug(f"[{image_stem}][{name}] 保存标注图: {out_path}")
        else:
            # 无检测结果，直接保存原图到 tags/
            out_path = tags_out_dir / f"{eng_name}_det.jpg"
            cv2.imwrite(str(out_path), sub_img)
            logger.debug(f"[{image_stem}][{name}] 无检测结果，保存原图: {out_path}")

    # 压缩象限图到 1080p（减少后续视觉模型 token 消耗）
    compress_quadrants_to_1080p(quadrants_dir)

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

    # ---- 按 tags/ 中标注图数量分组成败 ----
    out_path = Path(preprocessed_dir)
    success_dir = out_path / "_success"
    fail_dir = out_path / "_fail"
    success_dir.mkdir(parents=True, exist_ok=True)
    fail_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0
    for subdir in sorted(out_path.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        det_files = (
            list((subdir / "tags").glob("*_det.jpg"))
            if (subdir / "tags").is_dir()
            else []
        )
        if len(det_files) >= 3:
            subdir.rename(success_dir / subdir.name)
            success_count += 1
        else:
            subdir.rename(fail_dir / subdir.name)
            fail_count += 1

    logger.info(f"分组完成: 成功={success_count} 失败={fail_count}")
    print(
        f"\n分组完成: 成功={success_count} → {success_dir}, 失败={fail_count} → {fail_dir}"
    )
