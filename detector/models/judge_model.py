"""多模态视觉理解 — 通过 OpenAI 兼容接口发送图片给多模态模型进行理解。"""

import base64
import json
from pathlib import Path

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from pydantic import BaseModel, Field

from detector.utils import logger


class ViolationResult(BaseModel):
    """交通违法判定结果。"""

    violated: bool = Field(description="是否违反交通灯（闯红灯）")
    reason: str = Field(description="判定理由")
    raw_response: str = Field(default="", description="模型原始流式回复全文")


class VisionClient:
    """多模态视觉理解客户端，封装 OpenAI 兼容接口的图片理解请求。

    使用 AsyncOpenAI 客户端，支持并发调用。
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        base_url: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 20000,
        temperature: float = 0.0,
    ) -> None:
        """初始化客户端。

        Args:
            model: 模型名称，默认 "gpt-4o"。
            base_url: API 基础 URL，为 None 时使用 OpenAI 默认地址。
            api_key: API 密钥，为 None 时从环境变量读取。
            max_tokens: 最大生成 token 数。
            temperature: 生成温度。
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def judge_violation(
        self,
        quadrant_images: dict[str, str],
        annotated_images: dict[str, str],
        suspect_image: str,
    ) -> ViolationResult:
        """判断嫌疑车辆是否违反交通灯（闯红灯）。

        将每个象限图 + 其标注了检测框的图片 + 嫌疑车辆图逐张发送给多模态模型，
        让模型根据时间顺序判断车辆是否闯红灯。

        Args:
            quadrant_images: 象限名 → 象限图片路径，如 {"左上": "/path/左上.jpg", ...}。
            annotated_images: 象限名 → 该象限标注了检测框的图片路径。
            suspect_image: 嫌疑车辆图片路径（右下象限）。

        Returns:
            ViolationResult 判定结果。
        """
        # 构建图片列表和说明
        image_paths = [
            quadrant_images["左上"],
            annotated_images["左上"],
            quadrant_images["右上"],
            annotated_images["右上"],
            quadrant_images["左下"],
            annotated_images["左下"],
            suspect_image,
        ]
        descriptions = [
            "- 第1张（左上，时间最早）：十字路口全景图",
            "  └ 左上象限交通灯检测标注图（框内为检测到的交通灯）",
            "- 第2张（右上，时间居中）：十字路口全景图",
            "  └ 右上象限交通灯检测标注图（框内为检测到的交通灯）",
            "- 第3张（左下，时间最晚）：十字路口全景图",
            "  └ 左下象限交通灯检测标注图（框内为检测到的交通灯）",
            "- 嫌疑车辆（右下）：嫌疑车辆图",
        ]

        prompt = (
            "你是一个交通违法判定助手。以下是同一十字路口同一角度但不同时间拍摄的三张全景图"
            "（按时间从早到晚排列），每张全景图后附有从该图中检测出的交通灯标注图"
            "（绿色框标注了检测到的交通灯位置和类别）。"
            "最后一张是嫌疑车辆图。\n\n"
            "重要提示：\n"
            "- 请重点参考交通灯标注图来判断信号灯状态，标注图中的检测框标出了交通灯的位置和类别，以标注图为准。\n"
            "- 全景图中可能存在其他车辆的违规行为，但这与当前嫌疑车辆无关，请仅针对嫌疑车辆进行判断。\n"
            "- 请独立判断嫌疑车辆是否闯红灯，不要被图片中其他车辆的违法行为干扰。\n"
            "- 只判断是否闯红灯，压线、违停等其他违法行为不在判定范围内。\n\n"
            "请按以下步骤分析：\n"
            "1. 逐张分析每张交通灯标注图，描述该时刻信号灯的状态（红灯/绿灯/黄灯）。\n"
            "2. 根据信号灯状态的时间变化，判断嫌疑车辆通过路口时信号灯是否为红灯。\n\n"
            "图片说明：\n" + "\n".join(descriptions) + "\n\n"
            "请按以下 JSON 格式回答（不要输出其他内容）：\n"
            '"violated": true/false, "reason": "判定理由"}'
        )

        # 构建 API 请求内容
        content: list[
            ChatCompletionContentPartImageParam | ChatCompletionContentPartTextParam
        ] = [ChatCompletionContentPartTextParam(type="text", text=prompt)]
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}
        for path in image_paths:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = Path(path).suffix.lower().lstrip(".")
            mime = f"image/{mime_map.get(ext, 'jpeg')}"
            content.append(
                ChatCompletionContentPartImageParam(
                    type="image_url",
                    image_url=ImageURL(url=f"data:{mime};base64,{b64}", detail="high"),
                )
            )

        logger.debug(
            f"[vision] 违法判定请求: {len(image_paths)} 张图片, "
            f"prompt 长度: {len(prompt)}"
        )

        # 流式调用，积累完整回复
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True,
            extra_body={"enable_thinking": True},
        )

        raw_chunks: list[str] = []
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                raw_chunks.append(delta.content)

        raw = "".join(raw_chunks)
        logger.debug(f"[vision] 回复长度: {len(raw)}")

        # 解析模型回复
        try:
            # 尝试从回复中提取 JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                return ViolationResult(**data, raw_response=raw)
        except Exception as e:
            logger.warning(f"[vision] 解析违法判定结果失败: {e}, 原始回复: {raw}")

        return ViolationResult(
            violated=False,
            reason=f"解析失败，原始回复: {raw}",
            raw_response=raw,
        )
