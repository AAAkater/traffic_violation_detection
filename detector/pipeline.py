"""检测流水线 — 编排图片分割、检测、合并、分类、保存全流程。"""

from datetime import datetime
from pathlib import Path

from ultralytics import YOLO

from detector.detection import detect_traffic_lights
from detector.filter import filter_upper_region
from detector.merger import merge_or_expand
from detector.saver import crop_and_save_traffic_lights, save_quadrants
from detector.splitter import split_image_into_4
from detector.utils import logger


def run(
    image_path: str,
    model_path: str,
    conf_threshold: float = 0.5,
    base_output_dir: str | None = None,
    image_stem: str | None = None,
) -> None:
    """执行完整的红绿灯检测流水线。

    1. 将大图分割为 4 个子图并保存
    2. 对每个子图分别检测红绿灯
    3. 合并同一灯杆上的检测框
    4. 分类正/背面并保存

    Args:
        image_path: 输入图片路径。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        base_output_dir: 输出根目录。若为 None，自动生成带时间戳的路径。
        image_stem: 图片标识名（不含扩展名），用于命名输出子目录。
    """
    model = YOLO(model_path)

    if base_output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = f"./output/{ts}"
        logger.info(f"本次检测时间戳: {ts}")
    else:
        logger.info(f"输出目录: {base_output_dir}")

    # 每张图片的输出子目录（按文件名区分）
    if image_stem is None:
        image_stem = Path(image_path).stem

    quadrants_dir = f"{base_output_dir}/{image_stem}/quadrants"
    crops_all_dir = f"{base_output_dir}/{image_stem}/crops_all"
    crops_dir = f"{base_output_dir}/{image_stem}/crops"

    # 1. 将大图分割为 4 个子图并保存
    quadrants = split_image_into_4(image_path)
    save_quadrants(quadrants, output_dir=quadrants_dir)

    # 2. 对每个子图分别检测红绿灯并裁剪保存
    for name, sub_img in quadrants:
        logger.info(f"[{image_stem}][{name}] 区域检测：")

        detections = detect_traffic_lights(
            model, sub_img, conf_threshold=conf_threshold
        )

        if not detections:
            logger.info("未检测到红绿灯。")
            continue

        # 仅保留置信度 >= 0.6 的检测结果
        total_detected = len(detections)
        detections = [d for d in detections if d["confidence"] >= 0.6]
        if len(detections) < total_detected:
            logger.info(f"低置信度过滤: {total_detected} → {len(detections)} 个")

        if not detections:
            logger.info("无高置信度红绿灯。")
            continue

        logger.info(f"检测到 {len(detections)} 个红绿灯")

        h, w = sub_img.shape[:2]

        # 仅保留图片中上部的红绿灯（下部多为背面/反射/误检）
        upper_detections, removed = filter_upper_region(detections, h, upper_ratio=0.5)
        if removed:
            logger.info(
                f"剔除 {len(removed)} 个下半区域检测框，"
                f"保留 {len(upper_detections)} 个上半区域"
            )

        if not upper_detections:
            logger.info("上半区域未检测到红绿灯。")
            continue

        for d in upper_detections:
            logger.info(f"  位置: {d['bbox']}, 置信度: {d['confidence']}")

        # 智能合并：近距离的合并为组，单飞的扩大以抓取完整灯组
        merged = merge_or_expand(upper_detections, w, h)
        group_count = len(merged)
        if group_count < len(upper_detections):
            logger.info(f"合并后: {len(upper_detections)} 个 → {group_count} 组")
        elif len(upper_detections) == 1:
            logger.info(
                f"单框已扩大: {upper_detections[0]['bbox']} → {merged[0]['bbox']}"
            )
        else:
            logger.info("多框未合并，已全部扩大")

        # 保存全部检测结果（未合并 + 不筛选正/背面）
        crop_and_save_traffic_lights(
            sub_img,
            detections,
            output_dir=crops_all_dir,
            prefix=f"traffic_light_{name}",
            skip_back_side=False,
        )

        # 保存合并后的正面红绿灯组（仅上半区域）
        crop_and_save_traffic_lights(
            sub_img,
            merged,
            output_dir=crops_dir,
            prefix=f"traffic_light_{name}",
            skip_back_side=True,
        )


def run_batch(
    dataset_dir: str,
    model_path: str,
    conf_threshold: float = 0.5,
    output_dir: str | None = None,
) -> None:
    """对文件夹下所有图片批量执行红绿灯检测。

    Args:
        dataset_dir: 图片文件夹路径。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        output_dir: 输出根目录。若为 None，自动生成带时间戳的路径。
    """
    dataset_path = Path(dataset_dir)
    if not dataset_path.is_dir():
        logger.error(f"文件夹不存在: {dataset_dir}")
        return

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    images = sorted(
        p for p in dataset_path.iterdir() if p.suffix.lower() in image_extensions
    )

    if not images:
        logger.warning(f"未找到图片文件: {dataset_dir}")
        return

    if output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./output/{ts}"

    total = len(images)
    logger.info(f"=== 批量检测开始，共 {total} 张图片 ===")

    for idx, img_path in enumerate(images, 1):
        logger.info(f"\n=== [{idx}/{total}] {img_path.name} ===")
        run(
            image_path=str(img_path),
            model_path=model_path,
            conf_threshold=conf_threshold,
            base_output_dir=output_dir,
            image_stem=img_path.stem,
        )

    logger.info(f"\n=== 批量检测完成，处理 {total} 张，结果: {output_dir} ===")
