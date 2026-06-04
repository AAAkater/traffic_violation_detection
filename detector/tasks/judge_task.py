"""判定任务数据模型 — 检测流水线与判定模块之间的数据传递结构。"""

from typing import Literal

from pydantic import BaseModel, Field


class JudgeTask(BaseModel):
    """一个待判定的违法检测任务。

    由检测流水线（生产者）产出，交由 VisionClient（消费者）判定。
    """

    sample_id: str = Field(description="样本唯一标识，如图片文件名（不含扩展名）")
    sample_dir: str = Field(
        description="样本输出目录，包含 quadrants/、crops/ 等子目录"
    )
    quadrant_images: dict[str, str] = Field(
        description="象限名 → 象限图片路径，如 {'左上': '/path/左上.jpg'}"
    )
    crop_images: dict[str, str] = Field(
        description="象限名 → 该象限裁剪出的交通灯图片路径"
    )
    suspect_image: str = Field(description="嫌疑车辆图片路径（右下象限）")
    status: Literal["pending", "judging", "done", "failed"] = Field(
        default="pending", description="任务状态"
    )


class JudgeResult(BaseModel):
    """判定结果 — 包含原始任务和判定输出。"""

    task: JudgeTask = Field(description="原始判定任务")
    violated: bool = Field(default=False, description="是否违反交通灯（闯红灯）")
    reason: str = Field(default="", description="判定理由")
    raw_response: str = Field(default="", description="模型原始流式回复全文")
    error: str | None = Field(default=None, description="如果判定失败，记录错误信息")

    @property
    def sample_id(self) -> str:
        return self.task.sample_id
