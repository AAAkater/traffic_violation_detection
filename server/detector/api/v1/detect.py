"""检测端点 — 上传图片，返回红绿灯检测框坐标和类别名称，结果持久化到数据库。"""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from detector.api.dep import DetectServiceDep
from detector.models.detect import DetectData
from detector.models.response import Response

router = APIRouter(tags=["detect"])


@router.post("/detect")
async def detect(
    image_file: Annotated[UploadFile, File(alias="image_file")],
    service: DetectServiceDep,
) -> Response[DetectData]:
    """上传原始图片，执行 YOLO 检测，返回所有检测框的坐标和类别名称，并保存到数据库。"""
    try:
        contents = await image_file.read()
        data = await service.detect(contents=contents, filename=image_file.filename)
        return Response(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
