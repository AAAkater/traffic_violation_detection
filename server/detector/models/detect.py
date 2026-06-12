"""检测相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """单个红绿灯检测结果（内部使用，含坐标属性）。"""

    bbox: list[float] = Field(description="[x1, y1, x2, y2] 边界框坐标")
    confidence: float = Field(description="检测置信度")
    class_name: str = Field(default="", description="类别名称，如 red/green/yellow/off/wait_on")

    @property
    def x1(self) -> float:
        return self.bbox[0]

    @property
    def y1(self) -> float:
        return self.bbox[1]

    @property
    def x2(self) -> float:
        return self.bbox[2]

    @property
    def y2(self) -> float:
        return self.bbox[3]

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class DetectionItem(BaseModel):
    """单个检测框结果。"""

    quadrant: str = Field(
        description="所属象限: top_left(左上-红灯区) / top_right(右上-绿灯区) / bottom_left(左下-黄灯区)"
    )
    bbox: list[float] = Field(description="[x1, y1, x2, y2] 边界框坐标（原始图片坐标系）")
    confidence: float = Field(description="检测置信度")
    class_name: str = Field(description="类别名称，如 red/green/yellow/off/wait_on")


class DetectData(BaseModel):
    """检测接口返回数据。"""

    image_id: str = Field(description="图片唯一标识，同一次检测的所有框共享此 ID")
    detections: list[DetectionItem] = Field(description="所有检测框列表")
