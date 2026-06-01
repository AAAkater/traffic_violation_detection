"""检测框空间过滤 — 按位置筛选红绿灯 bbox。"""


def filter_upper_region(
    detections: list[dict],
    image_height: int,
    upper_ratio: float = 0.5,
) -> tuple[list[dict], list[dict]]:
    """仅保留图片中上部的红绿灯，剔除下半区域的检测框。

    在行车记录仪画面中，红绿灯通常位于画面上方（安装在高处），
    下半区域的检测框往往是背面、反射或误检，应予以剔除。

    Args:
        detections: 检测结果列表，每条含 "bbox" 字段。
        image_height: 图片高度（像素）。
        upper_ratio: 判定"上部"的占比线，默认 0.5 即上半 50%。

    Returns:
        (kept, removed): 保留的检测框列表 + 被剔除的检测框列表。
    """
    cutoff = image_height * upper_ratio

    kept: list[dict] = []
    removed: list[dict] = []

    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        center_y = (y1 + y2) / 2
        if center_y < cutoff:
            kept.append(d)
        else:
            removed.append(d)

    return kept, removed
