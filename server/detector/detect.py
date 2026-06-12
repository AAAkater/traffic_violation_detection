"""检测流水线 — 编排检测、空间过滤、画框标注全流程。

接收预处理后的象限 PIL 图片，执行 YOLO 检测并返回标注图，
全程在内存中完成，不涉及文件 I/O。
"""

from __future__ import annotations

import time

import numpy as np
from PIL import Image

from detector.draw import draw_detections
from detector.filter import filter_spatial
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.utils import logger

# 检测顺序
DETECT_ORDER: list[str] = ["top_left", "top_right", "bottom_left"]


def detect_pipeline(
    quadrant_images: dict[str, Image.Image],
    model_path: str,
    device: str,
    conf_threshold: float = 0.5,
) -> tuple[dict[str, Image.Image], dict[str, list[Detection]]]:
    """对预处理后的象限图片执行红绿灯检测流水线。

    Args:
        quadrant_images: 象限名到 PIL Image 的映射，包含
            "top_left", "top_right", "bottom_left" 三个检测象限。
        model_path: YOLO 模型权重路径。
        device: 推理设备。
        conf_threshold: 检测置信度阈值。

    Returns:
        (annotated_images, raw_detections) 二元组。
        annotated_images — 标注图映射，key "{eng_name}_det"。
        raw_detections — 原始检测坐标字典。
    """
    t0 = time.perf_counter()
    detector = TrafficLightDetector(
        model_path,
        device=device,
        conf_threshold=conf_threshold,
    )

    per_quadrant_detections: dict[str, list[Detection]] = {}
    # 保存每个象限的原始 PIL 图片，用于后续画框
    quadrant_pil: dict[str, Image.Image] = {}

    for eng_name in DETECT_ORDER:
        if eng_name not in quadrant_images:
            logger.warning(f"缺少象限图: {eng_name}")
            continue

        pil_img = quadrant_images[eng_name]
        # PIL (RGB) → numpy (RGB) → BGR，供 YOLO 使用
        q_img = np.array(pil_img.convert("RGB"))[:, :, ::-1].copy()
        h, w = q_img.shape[:2]
        quadrant_pil[eng_name] = pil_img

        logger.debug(f"[{eng_name}] 检测中…")
        raw = detector.detect(q_img)

        if not raw:
            logger.debug(f"[{eng_name}] 检出 0 个")
            per_quadrant_detections[eng_name] = []
            continue

        logger.debug(
            f"[{eng_name}] YOLO检出 {len(raw)} 个: "
            + ", ".join(f"({d.width:.0f}×{d.height:.0f}@{d.confidence:.2f})" for d in raw)
        )

        vehicle = filter_spatial(
            raw,
            image_height=h,
            image_width=w,
            label=f"[{eng_name}]",
        )
        per_quadrant_detections[eng_name] = vehicle

        if vehicle:
            logger.debug(f"[{eng_name}] 检出成功, all={len(raw)} vehicle={len(vehicle)}")
        else:
            logger.debug(f"[{eng_name}] 未检出")

    # 在象限图上画检测框，收集标注图
    annotated_images: dict[str, Image.Image] = {}

    for eng_name, pil_img in quadrant_pil.items():
        if eng_name not in DETECT_ORDER:
            continue

        detections = per_quadrant_detections.get(eng_name, [])

        annotated = draw_detections(pil_img, detections) if detections else pil_img
        annotated_images[f"{eng_name}_det"] = annotated
        logger.debug(f"[{eng_name}] 标注图已生成")

    elapsed = time.perf_counter() - t0
    logger.info(f"[detect] YOLO检测流水线总耗时: {elapsed:.3f}s")

    return annotated_images, per_quadrant_detections
