"""违法判定端点 — 接收 image_id、provider_id 和 model，从数据库获取原图和检测框，画框后传给 LLM 判定，结果持久化到数据库。"""

from fastapi import APIRouter, HTTPException

from detector.api.dep import JudgeServiceDep
from detector.models.judge import JudgeData
from detector.models.response import Response

router = APIRouter(tags=["judge"])


@router.post("/judge")
async def judge(
    image_id: str,
    provider_id: int,
    model: str,
    service: JudgeServiceDep,
) -> Response[JudgeData]:
    """接收 image_id、provider_id 和 model，从数据库获取原图和检测框，画框后传给 LLM 判定。

    Args:
        image_id: 检测接口返回的图片唯一标识。
        provider_id: 模型提供商 ID。
        model: 模型名称。
        service: 判定业务逻辑服务。
    """
    try:
        data = await service.judge(image_id=image_id, provider_id=provider_id, model=model)
        return Response(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
