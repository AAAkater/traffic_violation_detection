"""检测流水线 — 编排检测、空间过滤、画框标注全流程。

接收预处理后的象限 PIL 图片，执行 YOLO 检测并返回标注图，
全程在内存中完成，不涉及文件 I/O。
"""

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

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


def run(
    quadrant_images: dict[str, Image.Image],
    model_path: str,
    conf_threshold: float = 0.5,
    device: str | None = None,
) -> tuple[DetectionStats, dict[str, Image.Image]]:
    """对预处理后的象限图片执行红绿灯检测流水线。

    Args:
        quadrant_images: 象限名到 PIL Image 的映射，由 preprocess_single 返回。
            包含 "topleft", "topright", "bottomleft" 三个检测象限。
        model_path: YOLO 模型权重路径。
        conf_threshold: 检测置信度阈值。
        device: 推理设备。

    Returns:
        (DetectionStats, annotated_images) — 检测统计 + 标注图映射。
        annotated_images 的 key 为 "{eng_name}_det"，如 "topleft_det"。
    """
    detector = TrafficLightDetector(
        model_path, conf_threshold=conf_threshold, device=device
    )

    stats = DetectionStats()
    per_quadrant_detections: dict[str, list[Detection]] = {}
    # 保存每个象限的原始 PIL 图片，用于后续画框
    quadrant_pil: dict[str, Image.Image] = {}

    for eng_name, cn_name in QUADRANT_NAME_MAP.items():
        if eng_name not in quadrant_images:
            logger.warning(f"缺少象限图: {eng_name}")
            continue

        pil_img = quadrant_images[eng_name]
        # PIL (RGB) → numpy (RGB) → BGR，供 YOLO 使用
        q_img = np.array(pil_img.convert("RGB"))[:, :, ::-1].copy()
        h, w = q_img.shape[:2]
        quadrant_pil[cn_name] = pil_img

        logger.debug(f"[{cn_name}] 检测中…")
        raw = detector.detect(q_img)

        if not raw:
            logger.debug(f"[{cn_name}] 检出 0 个")
            per_quadrant_detections[cn_name] = []
            continue

        logger.debug(
            f"[{cn_name}] YOLO检出 {len(raw)} 个: "
            + ", ".join(
                f"({d.width:.0f}×{d.height:.0f}@{d.confidence:.2f})" for d in raw
            )
        )

        vehicle = detector.filter_spatial(
            raw,
            image_height=h,
            image_width=w,
            label=f"[{cn_name}]",
        )
        per_quadrant_detections[cn_name] = vehicle
        stats.all += len(raw)
        stats.vehicle += len(vehicle)

        if vehicle:
            logger.debug(f"[{cn_name}] 检出成功, all={len(raw)} vehicle={len(vehicle)}")
        else:
            logger.debug(f"[{cn_name}] 未检出")

    # 在象限图上画检测框，收集标注图
    annotated_images: dict[str, Image.Image] = {}

    for cn_name, pil_img in quadrant_pil.items():
        if cn_name not in DETECT_ORDER:
            continue

        eng_name = QUADRANT_NAME_RMAP[cn_name]
        detections = per_quadrant_detections.get(cn_name, [])

        annotated = (
            detector.draw_detections(pil_img, detections) if detections else pil_img
        )
        annotated_images[f"{eng_name}_det"] = annotated
        logger.debug(f"[{cn_name}] 标注图已生成")

    return stats, annotated_images
