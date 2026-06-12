"""多模态视觉理解 — 通过 OpenAI 兼容接口发送图片给多模态模型进行理解。"""

import base64
import io
import json
import time
from collections.abc import Sequence

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_content_part_image_param import ImageURL
from PIL import Image

from detector.utils import logger


class VisionClient:
    """多模态视觉理解客户端，封装 OpenAI 兼容接口的图片理解请求。"""

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def judge_violation(
        self,
        annotated_images: Sequence[Image.Image],
        suspect_image: Image.Image,
        system_prompt: str | None = None,
    ) -> tuple[bool, str, str]:
        """判断嫌疑车辆是否违反交通灯（闯红灯）。

        将 3 张标注了检测框的象限图 + 嫌疑车辆图发送给多模态模型。

        Args:
            annotated_images: 3 张标注了检测框的 PIL 图片（左上、右上、左下）。
            suspect_image: 嫌疑车辆 PIL 图片（右下象限）。
            system_prompt: 自定义系统提示词。若为 None 则使用内置默认提示词。

        Returns:
            (violated, reason, raw_response) 三元组。
        """
        descriptions = [
            "- 第1张（左上，时间最早）：交通灯检测标注图",
            "- 第2张（右上，时间居中）：交通灯检测标注图",
            "- 第3张（左下，时间最晚）：交通灯检测标注图",
            "- 第4张（右下）：嫌疑车辆图",
        ]

        _default_prompt = (
            "你是一个交通违法判定助手。以下是同一十字路口同一角度但不同时间拍摄的三张交通灯检测标注图"
            "（按时间从早到晚排列），检测框中标注了交通灯的位置和类别（red/green/yellow/off/wait_on）。"
            "最后一张是嫌疑车辆图。\n\n"
            "重要提示：\n"
            "- 图片上可能存在系统自动标注的违规提示文字如'闯红灯'等，这些文字是自动生成的，"
            "可能不准确，请忽略它们，不要将其作为判断依据。\n"
            "- 同一时刻可能检测到多组交通灯（对应左转、直行、右转等不同方向），"
            "它们可能同时出现 red 和 green，这是正常的——不同方向的信号相位不同。\n"
            "- 请独立判断嫌疑车辆是否闯红灯，不要被图片中其他车辆的违法行为干扰。\n"
            "- 只判断是否闯红灯，压线、违停等其他违法行为不在判定范围内。\n\n"
            "请严格按以下步骤分析（每一步都不可跳过）：\n"
            "1. 观察第4张嫌疑车辆图，判断嫌疑车辆正在左转还是直行"
            "（观察车辆在图片中的位置、行驶轨迹、是否在左转车道等）。\n"
            "2. 逐张分析三张检测标注图，列出所有检测框的标签和大致位置"
            "（左侧/右侧，区分不同组的信号灯）。\n"
            "3. 根据车辆的行驶方向（左转或直行），确定应该参考哪一组信号灯"
            "（左转车参考左转灯，直行车参考直行灯）。\n"
            "4. 看该组信号灯在三张图中的变化：如果车辆通过路口时其对应方向的灯是 red，"
            "则判定为闯红灯；如果是 green，则不违规。\n\n"
            "图片说明：\n" + "\n".join(descriptions) + "\n\n"
            "请按以下 JSON 格式回答（不要输出其他内容）：\n"
            '{"violated": true/false, "reason": "判定理由"}'
        )

        prompt = system_prompt if system_prompt is not None else _default_prompt

        # 构建 API 请求内容
        content: list[ChatCompletionContentPartImageParam | ChatCompletionContentPartTextParam] = [
            ChatCompletionContentPartTextParam(type="text", text=prompt)
        ]

        for img in [*annotated_images, suspect_image]:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            content.append(
                ChatCompletionContentPartImageParam(
                    type="image_url",
                    image_url=ImageURL(url=f"data:image/jpeg;base64,{b64}", detail="high"),
                )
            )

        logger.debug(f"[vision] 违法判定请求: {len(annotated_images) + 1} 张图片, prompt 长度: {len(prompt)}")

        # 流式调用，积累完整回复
        t0 = time.perf_counter()
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
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
        elapsed = time.perf_counter() - t0
        logger.info(f"[vision] LLM推理耗时: {elapsed:.3f}s, 回复长度: {len(raw)}")

        # 解析模型回复
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                return data.get("violated", False), data.get("reason", ""), raw
        except Exception as e:
            logger.warning(f"[vision] 解析违法判定结果失败: {e}, 原始回复: {raw}")

        return False, f"解析失败，原始回复: {raw}", raw
