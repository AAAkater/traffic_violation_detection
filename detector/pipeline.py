"""检测流水线 — 编排图片分割、检测、合并、分类、保存全流程。"""

import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field
from tqdm import tqdm

from detector.classifier import classify_and_filter_back
from detector.merger import merge_or_expand
from detector.models import TrafficLightDetector
from detector.models.detect_model import Detection
from detector.utils import image_tools, logger
from detector.utils.image_tools import (
    compress_image_to_1080p,
    compress_quadrants_to_1080p,
    crop_and_save_traffic_lights,
    crop_upper_region,
    save_cropped_region,
)


class DetectionStats(BaseModel):
    """单张图片的检测统计结果。"""

    all: int = Field(default=0, description="YOLO 原始检出总数")
    vehicle: int = Field(default=0, description="正面机动车灯数量")


def run(
    image_path: str,
    model_path: str,
    conf_threshold: float = 0.5,
    base_output_dir: str | None = None,
    image_stem: str | None = None,
) -> DetectionStats:
    """执行完整的红绿灯检测流水线。

    1. 将大图分割为 4 个子图并保存
    2. 裁剪子图上半区域（去掉下半 + 左右边缘）
    3. 对裁剪区域执行 YOLO 检测，坐标映射回原图
    4. 分类正/背面并保存
    5. 合并同一灯杆上的检测框

    Args:
        image_path: 输入图片路径。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        base_output_dir: 输出根目录。若为 None，自动生成带时间戳的路径。
        image_stem: 图片标识名（不含扩展名），用于命名输出子目录。

    Returns:
        DetectionStats 统计信息。
    """
    detector = TrafficLightDetector(model_path, conf_threshold=conf_threshold)

    if base_output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = f"./output/{ts}"
        logger.info(f"本次检测时间戳: {ts}")

    if image_stem is None:
        image_stem = Path(image_path).stem

    quadrants_dir = f"{base_output_dir}/{image_stem}/quadrants"
    cropped_dir = f"{base_output_dir}/{image_stem}/cropped"
    crops_all_dir = f"{base_output_dir}/{image_stem}/crops_all"
    crops_dir = f"{base_output_dir}/{image_stem}/crops"
    # 各筛选步骤被踢掉的图片存放根目录
    filter_save_dir = f"{base_output_dir}/{image_stem}"

    # 1. 分割
    quadrants = image_tools.split_image_into_4(image_path)
    image_tools.save_quadrants(quadrants, output_dir=quadrants_dir)

    stats = DetectionStats()

    # ------------------------------------------------------------------
    # 2. 依次在 左上 → 右上 → 左下 上执行完整检测流水线，
    #    直到某个象限成功检出并合并为止。
    #    三者为同一摄像头同一角度不同时间的拍照，交通灯位置相同，
    #    检出成功后，其余象限直接复用合并 bbox 裁剪。
    # ------------------------------------------------------------------

    def _detect_quadrant(
        q_name: str,
        q_img: np.ndarray,
    ) -> tuple[list[Detection], list[Detection]]:
        """对单个象限执行完整管线（裁剪 → YOLO → 分类 → 合并）。

        先裁剪上半区域再送入 YOLO，减少检测范围、提高速度和准确性。
        各步骤的保存在函数内部完成。

        Returns:
            (raw, merged): YOLO 原始检出（坐标已映射回原图）+ 合并后的机动车灯。
        """
        logger.debug(f"[{image_stem}][{q_name}] 检测中…")

        # 先裁剪上半区域（去掉下半 + 左右边缘），再送入 YOLO
        cropped, offset_y, offset_x = crop_upper_region(
            q_img, upper_ratio=0.5, edge_ratio=0.20
        )
        save_cropped_region(cropped, f"{cropped_dir}/{q_name}.jpg")

        raw = detector.detect(cropped)

        if not raw:
            logger.debug(f"[{image_stem}][{q_name}] 检出 0 个")
            return raw, []

        # 将裁剪区域内的坐标映射回原图坐标
        raw = [d.shift(dx=offset_x, dy=offset_y) for d in raw]

        h, w = q_img.shape[:2]
        _prefix = f"traffic_light_{q_name}"
        _label = f"[{image_stem}][{q_name}]"

        # 保存 YOLO 原始检出（在原图上裁剪）
        crop_and_save_traffic_lights(
            q_img,
            raw,
            output_dir=crops_all_dir,
            prefix=_prefix,
        )

        logger.debug(
            f"[{image_stem}][{q_name}] YOLO检出 {len(raw)} 个: "
            + ", ".join(
                f"({d.width:.0f}×{d.height:.0f}@{d.confidence:.2f})" for d in raw
            )
        )

        # 正/背面分类（内部保存被剔除的背面裁剪图）
        vehicle_detections, _ = classify_and_filter_back(
            raw,
            q_img,
            label=_label,
            save_dir=filter_save_dir,
            prefix=_prefix,
        )

        if not vehicle_detections:
            return raw, []

        # 合并 + 扩大
        merged = merge_or_expand(vehicle_detections, w, h)
        if not merged:
            logger.debug(
                f"[{image_stem}][{q_name}] 合并失败({len(vehicle_detections)} 个框不在同一水平线), 视为检测失败"
            )
        elif len(merged) < len(vehicle_detections):
            logger.debug(
                f"[{image_stem}][{q_name}] 合并: {len(vehicle_detections)} → {len(merged)} 组"
            )

        # 保存合并后的最终结果
        if merged:
            crop_and_save_traffic_lights(
                q_img,
                merged,
                output_dir=crops_dir,
                prefix=_prefix,
            )

        return raw, merged

    # 依次尝试 左上 → 右上 → 左下，直到成功检出
    primary_name: str | None = None
    shared_merged: list[Detection] = []

    for q_name, q_img in quadrants:
        if q_name == "右下":
            continue  # 右下不同角度，跳过
        raw, merged = _detect_quadrant(q_name, q_img)
        if merged:
            primary_name = q_name
            shared_merged = merged
            stats.all += len(raw)
            stats.vehicle += len(merged)
            logger.debug(
                f"[{image_stem}] 检出成功象限: {q_name}, "
                f"all={len(raw)} vehicle={len(merged)}"
            )
            break
        else:
            logger.debug(f"[{image_stem}][{q_name}] 未检出，尝试下一象限")

    # 其余象限复用合并 bbox 直接裁剪（左上/右上/左下 同角度，右下不同角度跳过）
    for name, sub_img in quadrants:
        if name == "右下":
            continue  # 右下不同角度，跳过

        if not shared_merged:
            logger.debug(f"[{image_stem}][{name}] 无共享合并 bbox，跳过")
            continue

        if name == primary_name:
            continue  # 已经保存过，跳过

        logger.debug(
            f"[{image_stem}][{name}] 复用 {primary_name} 的 {len(shared_merged)} 个合并 bbox 裁剪"
        )

        crop_and_save_traffic_lights(
            sub_img,
            shared_merged,
            output_dir=crops_dir,
            prefix=f"traffic_light_{name}",
        )
        stats.vehicle += len(shared_merged)

        logger.debug(f"[{image_stem}][{name}] 保存 vehicle={len(shared_merged)}")

    # 压缩象限图到 1080p（减少后续视觉模型 token 消耗）
    compress_quadrants_to_1080p(quadrants_dir)

    # 兜底：如果 crops 不足 3 个，用裁剪区域图填充到 fail 目录
    crops_path = Path(crops_dir)
    crop_files = list(crops_path.glob("*.jpg")) if crops_path.exists() else []
    if len(crop_files) < 3:
        # 兜底：crops 不足 3 个时，用裁剪区域图压缩到 1080p 后填充到 crops 目录
        crops_path.mkdir(parents=True, exist_ok=True)
        cropped_path = Path(cropped_dir)
        for cf in sorted(cropped_path.glob("*.jpg")):
            dest = crops_path / f"fallback_{cf.name}"
            result = compress_image_to_1080p(cf, dest)
            if result is None:
                shutil.copy2(cf, dest)
            logger.debug(f"[{image_stem}] 兜底保存裁剪区域图: {dest}")

    return stats


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
    logger.info(f"=== 批量检测开始，共 {total} 张，输出: {output_dir} ===")

    total_all = 0
    total_vehicle = 0
    total_skipped = 0

    # 进度条：只显示文件名和关键统计
    pbar = tqdm(images, desc="检测", unit="img", ncols=100)

    for img_path in pbar:
        stem = img_path.stem
        stats = run(
            image_path=str(img_path),
            model_path=model_path,
            conf_threshold=conf_threshold,
            base_output_dir=output_dir,
            image_stem=stem,
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
        f"  总处理: {total} 张\n"
        f"  总检出(crops_all): {total_all} 个\n"
        f"  正面机动车灯(crops): {total_vehicle} 个\n"
        f"  无检出: {total_skipped} 张\n"
        f"  结果目录: {output_dir}\n"
        f"{'=' * 50}"
    )
    print(summary)
    logger.info(summary.replace("\n", " | "))

    # ---- 按 crops 数量分组成败 ----
    out_path = Path(output_dir)
    success_dir = out_path / "_success"
    fail_dir = out_path / "_fail"
    success_dir.mkdir(parents=True, exist_ok=True)
    fail_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0
    for subdir in sorted(out_path.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        crop_files = list(subdir.glob("crops/*.jpg"))
        if len(crop_files) == 3:
            subdir.rename(success_dir / subdir.name)
            success_count += 1
        else:
            subdir.rename(fail_dir / subdir.name)
            fail_count += 1

    logger.info(f"分组完成: 成功={success_count} 失败={fail_count}")
    print(
        f"\n分组完成: 成功={success_count} → {success_dir}, 失败={fail_count} → {fail_dir}"
    )
