"""判定核心逻辑 — 读取已检测完成的样本目录，并发调用 LLM 判定。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Literal

from PIL import Image
from pydantic import BaseModel, Field
from tqdm import tqdm

from detector.models.judge_model import VisionClient
from detector.utils import logger

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


class JudgeTask(BaseModel):
    """一个待判定的违法检测任务。"""

    sample_id: str = Field(description="样本唯一标识")
    sample_dir: str = Field(description="样本输出目录")
    annotated_images: dict[str, str] = Field(
        description="象限名 → 该象限标注了检测框的图片路径"
    )
    suspect_image: str = Field(description="嫌疑车辆图片路径（右下象限）")
    status: Literal["pending", "judging", "done", "failed"] = Field(
        default="pending", description="任务状态"
    )


class JudgeResult(BaseModel):
    """判定结果 — 包含原始任务和判定输出。"""

    task: JudgeTask = Field(description="原始判定任务")
    violated: bool = Field(default=False, description="是否闯红灯")
    reason: str = Field(default="", description="判定理由")
    raw_response: str = Field(default="", description="模型原始回复全文")
    error: str | None = Field(default=None, description="判定失败时的错误信息")

    @property
    def sample_id(self) -> str:
        return self.task.sample_id


# ---------------------------------------------------------------------------
# 单任务判定
# ---------------------------------------------------------------------------


async def _judge_one(
    client: VisionClient,
    task: JudgeResult,
    semaphore: asyncio.Semaphore,
    pbar: tqdm | None = None,
) -> JudgeResult:
    """在信号量控制下执行单个判定任务。"""
    async with semaphore:
        task.task.status = "judging"
        try:
            # 从路径加载 PIL 图片
            annotated = [Image.open(p) for p in task.task.annotated_images.values()]
            suspect = Image.open(task.task.suspect_image)
            result = await client.judge_violation(
                annotated_images=annotated,
                suspect_image=suspect,
            )
            task.task.status = "done"
            return JudgeResult(
                task=task.task,
                violated=result.violated,
                reason=result.reason,
                raw_response=result.raw_response,
            )
        except Exception as e:
            task.task.status = "failed"
            logger.error(f"[judge] 判定失败 {task.task.sample_id}: {e}")
            return JudgeResult(task=task.task, error=str(e))
        finally:
            if pbar is not None:
                pbar.update(1)


# ---------------------------------------------------------------------------
# 批量判定入口
# ---------------------------------------------------------------------------


async def run_judge(
    preprocessed_dir: str,
    *,
    model: str = "qwen3.6-plus",
    base_url: str | None = None,
    api_key: str | None = None,
    concurrency: int = 5,
    max_tokens: int = 20000,
    temperature: float = 0.0,
) -> list[JudgeResult]:
    """对检测完成的样本目录批量执行违法判定。

    Args:
        preprocessed_dir: 预处理后的输出根目录（由 preprocess.py 生成，且已运行 detect.py）。
        model: 判定模型名称。
        base_url: 判定 API 基础 URL。
        api_key: 判定 API 密钥。
        concurrency: 判定并发数。
        max_tokens: 最大生成 token 数。
        temperature: 生成温度。

    Returns:
        判定结果列表。
    """
    base_path = Path(preprocessed_dir)
    sample_dirs = sorted(
        d for d in base_path.iterdir() if d.is_dir() and (d / "cropped").is_dir()
    )

    if not sample_dirs:
        logger.warning(f"未找到包含 cropped/ 的样本目录: {preprocessed_dir}")
        return []

    # 构建判定任务
    tasks: list[JudgeResult] = []
    for sample_dir in sample_dirs:
        stem = sample_dir.name

        # 收集标注图
        root = sample_dir
        annotated_images: dict[str, str] = {}
        missing = False
        for q, eng in [
            ("左上", "topleft"),
            ("右上", "topright"),
            ("左下", "bottomleft"),
        ]:
            det_path = root / "tags" / f"{eng}_det.jpg"
            if det_path.exists():
                annotated_images[q] = str(det_path)
            else:
                logger.warning(f"[judge] 缺少标注图: {det_path}")
                missing = True
                break
        if missing:
            continue

        suspect_path = root / "tags" / "bottomright.jpg"
        if not suspect_path.exists():
            logger.warning(f"[judge] 缺少嫌疑车辆图: {suspect_path}")
            continue

        tasks.append(
            JudgeResult(
                task=JudgeTask(
                    sample_id=stem,
                    sample_dir=str(sample_dir),
                    annotated_images=annotated_images,
                    suspect_image=str(suspect_path),
                )
            )
        )

    if not tasks:
        logger.warning("没有可判定的样本")
        return []

    logger.info(f"=== 判定开始，共 {len(tasks)} 个样本 ===")

    client = VisionClient(
        model=model,
        base_url=base_url,
        api_key=api_key,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    semaphore = asyncio.Semaphore(concurrency)
    pbar = tqdm(total=len(tasks), desc="判定", unit="task", ncols=100)

    coros = [_judge_one(client, t, semaphore, pbar) for t in tasks]
    results: list[JudgeResult] = await asyncio.gather(*coros)

    pbar.close()

    # 保存结果
    _save_results(results, preprocessed_dir)

    return results


def _save_results(results: list[JudgeResult], output_dir: str) -> None:
    """将判定结果保存到输出目录。"""
    out_path = Path(output_dir)

    summary_rows: list[dict] = []
    violated_count = 0
    failed_count = 0

    for r in results:
        sample_dir = Path(r.task.sample_dir)

        result_data = {
            "sample_id": r.task.sample_id,
            "violated": r.violated,
            "reason": r.reason,
            "raw_response": r.raw_response,
            "error": r.error,
        }
        result_file = sample_dir / "judge_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        summary_rows.append(result_data)
        if r.error:
            failed_count += 1
        elif r.violated:
            violated_count += 1

    # 保存汇总 JSON
    summary_file = out_path / "judge_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": len(results),
                "violated": violated_count,
                "not_violated": len(results) - violated_count - failed_count,
                "failed": failed_count,
                "results": summary_rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # 打印汇总
    total = len(results)
    not_violated = total - violated_count - failed_count
    summary_text = (
        f"\n{'=' * 50}\n"
        f"  判定完成\n"
        f"  总判定: {total} 个\n"
        f"  违法: {violated_count} 个\n"
        f"  未违法: {not_violated} 个\n"
        f"  失败: {failed_count} 个\n"
        f"  结果目录: {output_dir}\n"
        f"{'=' * 50}"
    )
    print(summary_text)
    logger.info(summary_text.replace("\n", " | "))
