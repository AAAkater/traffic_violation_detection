"""红绿灯检测 — 使用 YOLO 模型检测图片中的红绿灯。"""

import numpy as np
from ultralytics import YOLO


def detect_traffic_lights(
    model: YOLO,
    source: str | np.ndarray,
    conf_threshold: float = 0.5,
) -> list[dict]:
    """检测图片中的红绿灯，返回检测结果列表。

    可接受文件路径或 numpy 数组（BGR 格式）作为输入。

    Args:
        model: YOLO 模型实例。
        source: 图片路径或 numpy 数组。
        conf_threshold: 置信度阈值，低于此值的结果将被过滤。

    Returns:
        检测结果列表，每个元素包含 bbox、置信度等字段。
        格式: [{"bbox": [x1, y1, x2, y2], "confidence": 0.95}, ...]
    """
    TRAFFIC_LIGHT_CLASS = 9

    results = model.predict(source=source, classes=[TRAFFIC_LIGHT_CLASS], verbose=False)
    detections: list[dict] = []

    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            conf = box.conf.item()
            if conf < conf_threshold:
                continue
            detections.append(
                {
                    "bbox": box.xyxy.tolist()[0],
                    "confidence": round(conf, 3),
                }
            )

    return detections


def has_traffic_light(
    model: YOLO, source: str | np.ndarray, conf_threshold: float = 0.5
) -> bool:
    """判断图片中是否包含红绿灯。

    Args:
        model: YOLO 模型实例。
        source: 图片路径或 numpy 数组。
        conf_threshold: 置信度阈值。

    Returns:
        True 表示图片中有红绿灯，False 表示没有。
    """
    detections = detect_traffic_lights(model, source, conf_threshold)
    return len(detections) > 0
