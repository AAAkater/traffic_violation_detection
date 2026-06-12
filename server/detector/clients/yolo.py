"""红绿灯检测模型 — YOLO 加载与推理。"""

import os
import time
from pathlib import Path

import numpy as np
from modelscope.hub.file_download import model_file_download
from ultralytics import YOLO

from detector.utils import logger


class TrafficLightDetector:
    """红绿灯检测器：YOLO 模型加载与推理。

    Args:
        model_path: YOLO 模型权重路径。
        conf_threshold: 检测置信度阈值。
        device: 推理设备，"cuda" / "cpu" / "cuda:0" 等。
    """

    def __init__(
        self,
        model_path: str,
        device: str,
        conf_threshold: float = 0.5,
    ) -> None:
        self._device = device
        self._model = YOLO(model_path, verbose=False).to(device)
        self.conf_threshold = conf_threshold

    @staticmethod
    def ensure_model(model_path: str) -> None:
        """如果模型权重文件不存在，从 ModelScope 自动下载。"""
        path = Path(model_path)
        if path.is_file():
            logger.info(f"模型权重已存在: {model_path}")
            return

        logger.warning(f"模型权重不存在: {model_path}")
        slug = os.environ.get("MODELSCOPE_MODEL_SLUG", "AAAkater/tvd_yolo26")
        logger.info(f"正在从 ModelScope 下载: {slug}/{path.name} → {path.parent}")

        try:
            model_file_download(
                model_id=slug,
                file_path=path.name,
                cache_dir=str(path.parent),
                local_dir=str(path.parent),
            )
        except Exception as e:
            raise FileNotFoundError(f"无法下载模型权重 ({slug})，请检查网络或手动放置到 {path}。\n错误: {e}") from e

        logger.info(f"模型下载完成: {path}")

    def detect(self, source: str | np.ndarray) -> list[tuple[list[float], float, str]]:
        """检测图片中的红绿灯，返回检测结果列表。

        Returns:
            每个元素为 (bbox, confidence, class_name) 元组。
        """
        t0 = time.perf_counter()
        results = self._model.predict(source=source, verbose=False, device=self._device)
        elapsed = time.perf_counter() - t0
        logger.info(f"[YOLO] 推理耗时: {elapsed:.3f}s")
        raw: list[tuple[list[float], float, str]] = []

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                conf = box.conf.item()
                if conf < self.conf_threshold:
                    continue
                cls_id = int(box.cls.item())
                cls_name = self._model.names.get(cls_id, str(cls_id))
                raw.append((box.xyxy.tolist()[0], round(conf, 3), cls_name))

        return raw
