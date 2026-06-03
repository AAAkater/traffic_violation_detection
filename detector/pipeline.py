"""检测流水线 — 编排图片分割、检测、合并、分类、保存全流程。"""

from datetime import datetime
from pathlib import Path

from tqdm import tqdm
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
) -> dict:
    """执行完整的红绿灯检测流水线。

    1. 将大图分割为 4 个子图并保存
    2. 对每个子图分别检测红绿灯
    3. 合并同一灯杆上的检测框
    4. 分类正/背面/行人灯并保存

    Args:
        image_path: 输入图片路径。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        base_output_dir: 输出根目录。若为 None，自动生成带时间戳的路径。
        image_stem: 图片标识名（不含扩展名），用于命名输出子目录。

    Returns:
        {"all": n_all, "vehicle": n_vehicle} 统计信息。
    """
    model = YOLO(model_path, verbose=False)

    if base_output_dir is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_output_dir = f"./output/{ts}"
        logger.info(f"本次检测时间戳: {ts}")

    if image_stem is None:
        image_stem = Path(image_path).stem

    quadrants_dir = f"{base_output_dir}/{image_stem}/quadrants"
    crops_all_dir = f"{base_output_dir}/{image_stem}/crops_all"
    crops_dir = f"{base_output_dir}/{image_stem}/crops"
    # 各筛选步骤被踢掉的图片存放目录
    filtered_lower_dir = f"{base_output_dir}/{image_stem}/filtered_lower"  # 下半区域
    filtered_edge_dir = f"{base_output_dir}/{image_stem}/filtered_edge"  # 水平边缘
    filtered_back_dir = f"{base_output_dir}/{image_stem}/filtered_back"  # 背面

    # 1. 分割
    quadrants = split_image_into_4(image_path)
    save_quadrants(quadrants, output_dir=quadrants_dir)

    # 建立名称 → 子图的映射，方便按名取用
    quadrant_map = {name: img for name, img in quadrants}

    from detector.classifier import is_front_facing

    stats = {"all": 0, "vehicle": 0}

    # ------------------------------------------------------------------
    # 2. 左上：完整检测流水线（YOLO → 过滤 → 分类 → 合并），得到最终 bbox
    #    右上 / 左下 与 左上 为同一摄像头同一角度，交通灯位置相同，
    #    后续直接复用 左上 的合并后 bbox 裁剪，跳过重复检测。
    # ------------------------------------------------------------------
    # ---- 2a. 左上 完整检测 ----
    tl_name = "左上"
    tl_img = quadrant_map[tl_name]
    logger.debug(f"[{image_stem}][{tl_name}] 检测中…")

    shared_merged: list[dict] = []  # 合并后的 bbox，将复用于 右上/左下
    tl_raw: list[dict] = []  # YOLO 原始检出，用于 crops_all（不经过任何管线过滤）

    raw_detections = detect_traffic_lights(model, tl_img, conf_threshold=conf_threshold)
    tl_raw = raw_detections

    # ---- 保存 YOLO 原始检出到 crops_all（不筛选，仅 YOLO 原生结果） ----
    if tl_raw:
        crop_and_save_traffic_lights(
            tl_img,
            tl_raw,
            output_dir=crops_all_dir,
            prefix=f"traffic_light_{tl_name}",
            skip_back_side=False,
            skip_pedestrian=False,
        )
        stats["all"] += len(tl_raw)

    # ---- 管线过滤：上半区域 → 水平边缘 → 分类 → 合并 ----
    tl_detections = detect_traffic_lights(model, tl_img, conf_threshold=0.6)

    if tl_detections:
        h, w = tl_img.shape[:2]

        # 上半区域过滤
        upper_detections, removed = filter_upper_region(
            tl_detections, h, upper_ratio=0.5
        )
        if removed:
            logger.debug(
                f"[{image_stem}][{tl_name}] 剔除 {len(removed)} 个下半区域框, "
                f"保留 {len(upper_detections)} 个"
            )
            # 保存被踢掉的下半区域图片
            crop_and_save_traffic_lights(
                tl_img,
                removed,
                output_dir=filtered_lower_dir,
                prefix=f"traffic_light_{tl_name}",
                skip_back_side=False,
                skip_pedestrian=False,
            )

        if upper_detections:
            # 水平边缘过滤
            edge_ratio = 0.20
            center_detections: list[dict] = []
            edge_detections: list[dict] = []
            for d in upper_detections:
                x1b, y1b, x2b, y2b = d["bbox"]
                cx = (x1b + x2b) / 2
                if cx < w * edge_ratio or cx > w * (1 - edge_ratio):
                    edge_detections.append(d)
                else:
                    center_detections.append(d)

            if edge_detections:
                logger.debug(
                    f"[{image_stem}][{tl_name}] 剔除 {len(edge_detections)} 个边缘框(疑似行人灯), "
                    f"保留 {len(center_detections)} 个中间区域"
                )
                # 保存被踢掉的边缘区域图片
                crop_and_save_traffic_lights(
                    tl_img,
                    edge_detections,
                    output_dir=filtered_edge_dir,
                    prefix=f"traffic_light_{tl_name}",
                    skip_back_side=False,
                    skip_pedestrian=False,
                )

            if center_detections:
                logger.debug(
                    f"[{image_stem}][{tl_name}] YOLO检出 {len(center_detections)} 个: "
                    + ", ".join(
                        f"({d['bbox'][2] - d['bbox'][0]:.0f}×{d['bbox'][3] - d['bbox'][1]:.0f}@{d['confidence']:.2f})"
                        for d in center_detections
                    )
                )

                # 正/背面分类（仅排除背面）
                vehicle_detections = []
                back_detections = []
                for d in center_detections:
                    x1b, y1b, x2b, y2b = map(int, d["bbox"])
                    crop = tl_img[y1b:y2b, x1b:x2b]
                    if is_front_facing(crop):
                        vehicle_detections.append(d)
                    else:
                        w_box, h_box = x2b - x1b, y2b - y1b
                        logger.debug(
                            f"[{image_stem}][{tl_name}] 跳过 背面 ({w_box}×{h_box})"
                        )
                        back_detections.append(d)

                # 保存被踢掉的背面图片
                if back_detections:
                    crop_and_save_traffic_lights(
                        tl_img,
                        back_detections,
                        output_dir=filtered_back_dir,
                        prefix=f"traffic_light_{tl_name}",
                        skip_back_side=False,
                        skip_pedestrian=False,
                    )

                if vehicle_detections:
                    # 合并 + 扩大
                    shared_merged = merge_or_expand(vehicle_detections, w, h)
                    if not shared_merged:
                        logger.debug(
                            f"[{image_stem}][{tl_name}] 合并失败({len(vehicle_detections)} 个框不在同一水平线), 视为检测失败"
                        )
                    elif len(shared_merged) < len(vehicle_detections):
                        logger.debug(
                            f"[{image_stem}][{tl_name}] 合并: {len(vehicle_detections)} → {len(shared_merged)} 组"
                        )

                    if shared_merged:
                        crop_and_save_traffic_lights(
                            tl_img,
                            shared_merged,
                            output_dir=crops_dir,
                            prefix=f"traffic_light_{tl_name}",
                            skip_back_side=False,
                            skip_pedestrian=False,
                        )
                        stats["vehicle"] += len(shared_merged)

                        logger.debug(
                            f"[{image_stem}][{tl_name}] 保存 all={len(tl_raw)} vehicle={len(shared_merged)}"
                        )

    # ---- 2b. 右上 / 左下：复用 左上 的合并 bbox 直接裁剪 ----
    for name in ["右上", "左下"]:
        sub_img = quadrant_map[name]

        if not shared_merged:
            logger.debug(f"[{image_stem}][{name}] 无共享合并 bbox，跳过")
            continue

        logger.debug(
            f"[{image_stem}][{name}] 复用 左上 的 {len(shared_merged)} 个合并 bbox 裁剪"
        )

        crop_and_save_traffic_lights(
            sub_img,
            shared_merged,
            output_dir=crops_dir,
            prefix=f"traffic_light_{name}",
            skip_back_side=False,
            skip_pedestrian=False,
        )
        stats["vehicle"] += len(shared_merged)

        logger.debug(
            f"[{image_stem}][{name}] 保存 raw={len(tl_raw)} vehicle={len(shared_merged)}"
        )

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
        total_all += stats["all"]
        total_vehicle += stats["vehicle"]
        if stats["all"] == 0:
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
