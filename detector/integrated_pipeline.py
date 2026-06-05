"""整合流水线 — 检测（生产者）与判定（消费者）通过 asyncio.Queue 并发执行。

检测模块作为生产者（快），每完成一个样本就产出 JudgeTask 放入队列；
判定模块作为消费者（慢），以指定并发数从队列中取任务并执行。
两者通过 asyncio.Queue 协调，实现流水线式并发。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tqdm import tqdm

from detector.models.judge_model import ViolationResult, VisionClient
from detector.pipeline import run
from detector.tasks.judge_task import JudgeResult, JudgeTask
from detector.utils import logger

# ---------------------------------------------------------------------------
# 辅助：从 pipeline 输出目录构建 JudgeTask
# ---------------------------------------------------------------------------


def build_judge_task(
    sample_id: str,
    sample_dir: str,
) -> JudgeTask | None:
    """从 pipeline 输出的样本目录构建 JudgeTask。

    目录结构预期（由 preprocess.py + run() 生成）：
        sample_dir/
        ├── cropped/topleft.jpg, topright.jpg, bottomleft.jpg
        ├── tags/
        │   ├── bottomright.jpg
        │   ├── topleft_det.jpg
        │   ├── topright_det.jpg
        │   └── bottomleft_det.jpg
        └── quadrants/quadrant_左上.jpg, quadrant_右上.jpg, ...

    Args:
        sample_id: 样本唯一标识。
        sample_dir: 样本输出目录路径。

    Returns:
        JudgeTask 或 None（如果必要文件缺失）。
    """
    root = Path(sample_dir)
    quadrant_images: dict[str, str] = {}
    annotated_images: dict[str, str] = {}

    for q, eng in [("左上", "topleft"), ("右上", "topright"), ("左下", "bottomleft")]:
        # 象限图（由 run() 从 cropped/ 复制到 quadrants/）
        q_path = root / "quadrants" / f"quadrant_{q}.jpg"
        if q_path.exists():
            quadrant_images[q] = str(q_path)
        else:
            logger.warning(f"[judge] 缺少象限图: {q_path}")
            return None

        # 标注图：在象限图上画了检测框的图片
        det_path = root / "tags" / f"{eng}_det.jpg"
        if det_path.exists():
            annotated_images[q] = str(det_path)
        else:
            logger.warning(f"[judge] 缺少标注图: {det_path}")
            return None

    # 嫌疑车辆图（右下象限，由 run() 从 tags/ 复制到 quadrants/）
    suspect_path = root / "quadrants" / "quadrant_右下.jpg"
    if not suspect_path.exists():
        logger.warning(f"[judge] 缺少嫌疑车辆图: {suspect_path}")
        return None

    return JudgeTask(
        sample_id=sample_id,
        sample_dir=sample_dir,
        quadrant_images=quadrant_images,
        annotated_images=annotated_images,
        suspect_image=str(suspect_path),
    )


# ---------------------------------------------------------------------------
# 消费者：异步判定
# ---------------------------------------------------------------------------


async def _judge_one(
    client: VisionClient,
    task: JudgeTask,
    semaphore: asyncio.Semaphore,
    pbar: tqdm | None = None,
) -> JudgeResult:
    """在信号量控制下执行单个判定任务。

    Args:
        client: VisionClient 实例（使用 AsyncOpenAI）。
        task: 待判定的任务。
        semaphore: 并发控制信号量。
        pbar: 可选的进度条。

    Returns:
        JudgeResult 判定结果。
    """
    async with semaphore:
        task.status = "judging"
        try:
            result: ViolationResult = await client.judge_violation(
                quadrant_images=task.quadrant_images,
                annotated_images=task.annotated_images,
                suspect_image=task.suspect_image,
            )
            task.status = "done"
            return JudgeResult(
                task=task,
                violated=result.violated,
                reason=result.reason,
                raw_response=result.raw_response,
            )
        except Exception as e:
            task.status = "failed"
            logger.error(f"[judge] 判定失败 {task.sample_id}: {e}")
            return JudgeResult(
                task=task,
                error=str(e),
            )
        finally:
            if pbar is not None:
                pbar.update(1)


# ---------------------------------------------------------------------------
# 生产者：检测流水线（在线程池中运行同步代码）
# ---------------------------------------------------------------------------


async def _detect_producer(
    preprocessed_dir: str,
    model_path: str,
    conf_threshold: float,
    queue: asyncio.Queue[JudgeTask | None],
    pbar: tqdm | None = None,
) -> None:
    """检测生产者：逐个处理预处理后的样本目录，完成后将 JudgeTask 放入队列。

    检测完成后向队列放入 None 作为结束信号。

    Args:
        preprocessed_dir: 预处理后的输出根目录（由 preprocess.py 生成）。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        queue: 生产者-消费者队列。
        pbar: 可选的进度条。
    """
    base_path = Path(preprocessed_dir)
    sample_dirs = sorted(
        d for d in base_path.iterdir() if d.is_dir() and (d / "cropped").is_dir()
    )

    if not sample_dirs:
        logger.warning(f"未找到包含 cropped/ 的样本目录: {preprocessed_dir}")
        await queue.put(None)
        return

    logger.info(f"=== 检测开始，共 {len(sample_dirs)} 个样本 ===")

    for sample_dir in sample_dirs:
        stem = sample_dir.name

        # 在线程池中执行同步检测
        await asyncio.to_thread(
            run,
            sample_dir=str(sample_dir),
            model_path=model_path,
            conf_threshold=conf_threshold,
        )

        # 检测完成后尝试构建 JudgeTask
        task = build_judge_task(stem, str(sample_dir))
        if task is not None:
            await queue.put(task)
            logger.debug(f"[producer] 入队: {stem}")

        if pbar is not None:
            pbar.update(1)

    # 结束信号
    await queue.put(None)
    logger.info("=== 检测生产者结束 ===")


# ---------------------------------------------------------------------------
# 消费者：从队列取任务并并发判定
# ---------------------------------------------------------------------------


async def _judge_consumer(
    client: VisionClient,
    queue: asyncio.Queue[JudgeTask | None],
    concurrency: int,
    pbar: tqdm | None = None,
) -> list[JudgeResult]:
    """判定消费者：从队列取任务，以指定并发数执行判定。

    收到 None 结束信号后停止消费。

    Args:
        client: VisionClient 实例。
        queue: 生产者-消费者队列。
        concurrency: 最大并发数。
        pbar: 可选的进度条。

    Returns:
        判定结果列表。
    """
    semaphore = asyncio.Semaphore(concurrency)
    results: list[JudgeResult] = []
    pending: set[asyncio.Task[JudgeResult]] = set()

    while True:
        # 从队列取任务
        task = await queue.get()

        if task is None:
            # 生产者结束，等待所有进行中的判定完成
            break

        # 创建判定协程，受信号量控制
        coro = _judge_one(client, task, semaphore, pbar)
        atask = asyncio.create_task(coro)
        pending.add(atask)

        # 清理已完成的任务
        done = {t for t in pending if t.done()}
        for t in done:
            pending.discard(t)
            results.append(t.result())

    # 等待剩余任务完成
    if pending:
        done, _ = await asyncio.wait(pending)
        for t in done:
            results.append(t.result())

    return results


# ---------------------------------------------------------------------------
# 整合流水线入口
# ---------------------------------------------------------------------------


def run_pipeline(
    preprocessed_dir: str,
    model_path: str,
    *,
    conf_threshold: float = 0.5,
    # 判定模块参数
    judge: bool = True,
    judge_model: str = "gpt-4o",
    judge_base_url: str | None = None,
    judge_api_key: str | None = None,
    judge_concurrency: int = 5,
) -> list[JudgeResult]:
    """执行检测 + 判定整合流水线。

    先由 preprocess.py 预处理图片，再对本模块执行检测 + 判定。
    检测模块作为生产者（快），每完成一个样本就产出 JudgeTask 放入队列；
    判定模块作为消费者（慢），以指定并发数从队列中取任务并执行。
    两者通过 asyncio.Queue 并发运行，实现流水线式处理。

    Args:
        preprocessed_dir: 预处理后的输出根目录（由 preprocess.py 生成）。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        judge: 是否执行判定步骤。为 False 时仅做检测。
        judge_model: 判定模型名称。
        judge_base_url: 判定 API 基础 URL。
        judge_api_key: 判定 API 密钥。
        judge_concurrency: 判定并发数。

    Returns:
        判定结果列表（如果 judge=False 则为空列表）。
    """
    logger.info(f"=== 整合流水线开始，目录: {preprocessed_dir} ===")

    if not judge:
        # 仅检测模式：使用原有 run_batch
        from detector.pipeline import run_batch

        run_batch(
            preprocessed_dir=preprocessed_dir,
            model_path=model_path,
            conf_threshold=conf_threshold,
        )
        logger.info("判定步骤已跳过 (judge=False)")
        return []

    # ---- 检测 + 判定并发模式 ----
    client = VisionClient(
        model=judge_model,
        base_url=judge_base_url,
        api_key=judge_api_key,
    )

    results = asyncio.run(
        _run_pipeline_concurrent(
            preprocessed_dir=preprocessed_dir,
            model_path=model_path,
            conf_threshold=conf_threshold,
            client=client,
            judge_concurrency=judge_concurrency,
        )
    )

    # ---- 保存判定结果 ----
    _save_results(results, preprocessed_dir)

    return results


async def _run_pipeline_concurrent(
    preprocessed_dir: str,
    model_path: str,
    conf_threshold: float,
    client: VisionClient,
    judge_concurrency: int,
) -> list[JudgeResult]:
    """并发运行检测生产者和判定消费者。

    Args:
        preprocessed_dir: 预处理后的输出根目录（由 preprocess.py 生成）。
        model_path: YOLO 模型权重路径。
        conf_threshold: YOLO 检测置信度阈值。
        client: VisionClient 实例。
        judge_concurrency: 判定并发数。

    Returns:
        判定结果列表。
    """
    queue: asyncio.Queue[JudgeTask | None] = asyncio.Queue(
        maxsize=judge_concurrency * 2
    )

    det_pbar = tqdm(desc="检测", unit="img", ncols=100)
    judge_pbar = tqdm(desc="判定", unit="task", ncols=100)

    # 生产者和消费者并发运行
    producer_task = asyncio.create_task(
        _detect_producer(
            preprocessed_dir=preprocessed_dir,
            model_path=model_path,
            conf_threshold=conf_threshold,
            queue=queue,
            pbar=det_pbar,
        )
    )

    consumer_task = asyncio.create_task(
        _judge_consumer(
            client=client,
            queue=queue,
            concurrency=judge_concurrency,
            pbar=judge_pbar,
        )
    )

    # 等待生产者完成
    await producer_task
    det_pbar.close()

    # 等待消费者完成
    results = await consumer_task
    judge_pbar.close()

    return results


def _save_results(results: list[JudgeResult], output_dir: str) -> None:
    """将判定结果保存到输出目录。

    每个样本的判定结果保存为 JSON 文件，同时生成汇总 CSV。

    Args:
        results: 判定结果列表。
        output_dir: 输出根目录。
    """
    out_path = Path(output_dir)

    # 汇总数据
    summary_rows: list[dict] = []
    violated_count = 0
    failed_count = 0

    for r in results:
        sample_dir = Path(r.task.sample_dir)

        # 保存单样本结果 JSON
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
