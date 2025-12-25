import datetime
import json
import os
import sys
import threading
from concurrent import futures

import grpc
import psycopg2
import yaml
from loguru import logger

from block_chain import analyse, collect_binance, collect_uniswap, process_prices
from block_chain.task import check_task

# 导入生成的代码
from protos.task_pb2 import TaskResponse, TaskStatus
from protos.task_pb2_grpc import TaskServiceServicer, add_TaskServiceServicer_to_server

# 导入数据收集模块

BASE_DIR = os.path.dirname(__file__)
with open(
    os.path.join(BASE_DIR, "config", "config.yaml"), "r", encoding="utf-8"
) as cfg_file:
    CONFIG = yaml.safe_load(cfg_file)
DB_CONFIG = CONFIG.get("db", {})
WORKER_PORT = str(CONFIG.get("worker_port", 50052))

STATUS_LABELS = {
    TaskStatus.TASK_STATUS_RUNNING: "RUNNING",
    TaskStatus.TASK_STATUS_SUCCESS: "SUCCESS",
    TaskStatus.TASK_STATUS_FAILED: "FAILED",
    TaskStatus.TASK_STATUS_CANCELED: "CANCELED",
}


def _get_db_connection():
    return psycopg2.connect(
        host=DB_CONFIG.get("host"),
        port=DB_CONFIG.get("port"),
        dbname=DB_CONFIG.get("database"),
        user=DB_CONFIG.get("username"),
        password=DB_CONFIG.get("password"),
    )


def log_task_event(task_id: str, level: str, message: str):
    if not task_id:
        return
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM tasks WHERE task_id = %s LIMIT 1", (task_id,))
            row = cur.fetchone()
            if not row:
                return
            cur.execute(
                "INSERT INTO task_logs (task_id, timestamp, level, message) VALUES (%s, NOW(), %s, %s)",
                (row[0], level, message),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("写入任务日志失败: %s", exc)


def mark_task_started(task_id: str):
    if not task_id:
        return
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET started_at = COALESCE(started_at, NOW()) WHERE task_id = %s",
                (task_id,),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("更新任务开始时间失败: %s", exc)


def mark_task_finished(task_id: str, status: TaskStatus, summary: str | None = None):
    if not task_id:
        return
    status_label = STATUS_LABELS.get(status)
    if not status_label:
        return
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = %s,
                    finished_at = NOW(),
                    duration_seconds = EXTRACT(EPOCH FROM NOW() - COALESCE(started_at, queued_at)),
                    log_summary = COALESCE(%s, log_summary)
                WHERE task_id = %s
                """,
                (status_label, summary, task_id),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("更新任务结束状态失败: %s", exc)


class TaskService(TaskServiceServicer):
    """实现 TaskService 的 gRPC 服务"""

    def CollectBinance(self, request, context):
        """
        收集币安数据
        在后台线程中执行任务，立即返回运行状态
        """
        task_id = request.task_id
        import_percentage = request.import_percentage
        chunk_size = request.chunk_size

        logger.info(
            f"收到收集币安数据请求: task_id={task_id}, "
            f"import_percentage={import_percentage}, chunk_size={chunk_size}"
        )

        # 获取 CSV 文件路径（相对于 data 目录）
        csv_path = os.path.join(os.path.dirname(__file__), "ETHUSDT-trades-2025-09.csv")

        def run_task():
            """在后台线程中执行任务"""
            try:
                logger.info(f"开始执行任务 {task_id}: 收集币安数据")
                mark_task_started(task_id)
                log_task_event(task_id, "INFO", "开始收集 Binance 数据")
                collect_binance.collect_binance(
                    task_id=task_id,
                    csv_path=csv_path,
                    import_percentage=import_percentage,
                    chunk_size=chunk_size,
                )
                # 检查任务是否被取消
                if check_task(task_id):
                    logger.info(f"任务 {task_id} 已被取消，不标记为成功")
                    log_task_event(task_id, "INFO", "任务被取消")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_CANCELED, "任务被取消"
                    )
                else:
                    logger.info(f"任务 {task_id} 执行成功: 收集币安数据")
                    log_task_event(task_id, "INFO", "收集 Binance 数据完成")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_SUCCESS, "Binance 数据导入完成"
                    )
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")
                log_task_event(task_id, "ERROR", f"收集 Binance 数据失败: {e}")
                mark_task_finished(task_id, TaskStatus.TASK_STATUS_FAILED, str(e))

        # 在后台线程中启动任务
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # 立即返回运行状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.TASK_STATUS_RUNNING,
        )

    def CollectBinanceByDate(self, request, context):
        """
        按日期收集币安数据
        在后台线程中执行任务，立即返回运行状态
        """
        task_id = request.task_id
        start_ts = request.start_ts
        end_ts = request.end_ts

        logger.info(
            f"收到按日期收集币安数据请求: task_id={task_id}, "
            f"start_ts={start_ts}, end_ts={end_ts}"
        )

        def run_task():
            """在后台线程中执行任务"""
            try:
                logger.info(f"开始执行任务 {task_id}: 按日期收集币安数据")
                mark_task_started(task_id)
                log_task_event(task_id, "INFO", "开始按日期收集 Binance 数据")
                collect_binance.collect_binance_by_date(
                    task_id=task_id,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                # 检查任务是否被取消
                if check_task(task_id):
                    logger.info(f"任务 {task_id} 已被取消，不标记为成功")
                    log_task_event(task_id, "INFO", "任务被取消")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_CANCELED, "任务被取消"
                    )
                else:
                    logger.info(f"任务 {task_id} 执行成功: 按日期收集币安数据")
                    log_task_event(task_id, "INFO", "按日期收集 Binance 数据完成")
                    mark_task_finished(
                        task_id,
                        TaskStatus.TASK_STATUS_SUCCESS,
                        "Binance 数据按日期收集完成",
                    )
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")
                log_task_event(task_id, "ERROR", f"按日期收集 Binance 数据失败: {e}")
                mark_task_finished(task_id, TaskStatus.TASK_STATUS_FAILED, str(e))

        # 在后台线程中启动任务
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # 立即返回运行状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.TASK_STATUS_RUNNING,
        )

    def CollectUniswap(self, request, context):
        """
        收集 Uniswap 数据
        在后台线程中执行任务，立即返回运行状态
        """
        task_id = request.task_id
        pool_address = request.pool_address
        start_ts = request.start_ts
        end_ts = request.end_ts

        logger.info(
            f"收到收集 Uniswap 数据请求: task_id={task_id}, "
            f"pool_address={pool_address}, start_ts={start_ts}, end_ts={end_ts}"
        )

        def run_task():
            """在后台线程中执行任务"""
            try:
                logger.info(f"开始执行任务 {task_id}: 收集 Uniswap 数据")
                mark_task_started(task_id)
                log_task_event(task_id, "INFO", "开始收集 Uniswap 数据")
                collect_uniswap.collect_uniswap(
                    task_id=task_id,
                    pool_address=pool_address,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                # 检查任务是否被取消
                if check_task(task_id):
                    logger.info(f"任务 {task_id} 已被取消，不标记为成功")
                    log_task_event(task_id, "INFO", "任务被取消")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_CANCELED, "任务被取消"
                    )
                else:
                    logger.info(f"任务 {task_id} 执行成功: 收集 Uniswap 数据")
                    log_task_event(task_id, "INFO", "收集 Uniswap 数据完成")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_SUCCESS, "Uniswap 数据采集完成"
                    )
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")
                log_task_event(task_id, "ERROR", f"收集 Uniswap 数据失败: {e}")
                mark_task_finished(task_id, TaskStatus.TASK_STATUS_FAILED, str(e))

        # 在后台线程中启动任务
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # 立即返回运行状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.TASK_STATUS_RUNNING,
        )

    def ProcessPrices(self, request, context):
        """
        处理价格数据
        在后台线程中执行任务，立即返回运行状态
        """
        task_id = request.task_id
        start_date = request.start_date
        end_date = request.end_date
        aggregation_interval = request.aggregation_interval
        overwrite = request.overwrite
        db_overrides = dict(request.db_overrides)

        logger.info(
            f"收到处理价格数据请求: task_id={task_id}, "
            f"start_date={start_date}, end_date={end_date}, "
            f"aggregation_interval={aggregation_interval}, overwrite={overwrite}"
        )

        def run_task():
            """在后台线程中执行任务"""
            try:
                logger.info(f"开始执行任务 {task_id}: 处理价格数据")

                # 将 int32 时间戳转换为日期字符串
                # 假设 start_date 和 end_date 是 Unix 时间戳（秒）
                start_date_str = None
                end_date_str = None

                if start_date:
                    dt = datetime.datetime.fromtimestamp(
                        start_date, tz=datetime.timezone.utc
                    )
                    start_date_str = dt.isoformat()

                if end_date:
                    dt = datetime.datetime.fromtimestamp(
                        end_date, tz=datetime.timezone.utc
                    )
                    end_date_str = dt.isoformat()

                # 准备参数
                kwargs = {
                    "aggregation_interval": (
                        aggregation_interval if aggregation_interval else "minute"
                    ),
                    "overwrite": overwrite,
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                }

                # 合并 db_overrides（如果有）
                if db_overrides:
                    kwargs.update(db_overrides)

                process_prices.run_process_prices(task_id=task_id, **kwargs)
                # 检查任务是否被取消
                if check_task(task_id):
                    logger.info(f"任务 {task_id} 已被取消，不标记为成功")
                    log_task_event(task_id, "INFO", "任务被取消")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_CANCELED, "任务被取消"
                    )
                else:
                    logger.info(f"任务 {task_id} 执行成功: 处理价格数据")
                    log_task_event(task_id, "INFO", "处理价格数据完成")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_SUCCESS, "价格数据处理完成"
                    )
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")

        # 在后台线程中启动任务
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # 立即返回运行状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.TASK_STATUS_RUNNING,
        )

    def Analyse(self, request, context):
        """
        分析数据
        在后台线程中执行任务，立即返回运行状态
        """
        task_id = request.task_id
        batch_id = request.batch_id
        overwrite = request.overwrite
        strategy_json = request.strategy_json

        logger.info(
            f"收到分析数据请求: task_id={task_id}, "
            f"batch_id={batch_id}, overwrite={overwrite}"
        )

        def run_task():
            """在后台线程中执行任务"""
            try:
                logger.info(f"开始执行任务 {task_id}: 分析数据")

                # 解析策略 JSON
                strategy_params = {}
                if strategy_json:
                    try:
                        strategy_params = json.loads(strategy_json)
                    except json.JSONDecodeError as e:
                        logger.error(f"解析策略 JSON 失败: {e}")
                        raise ValueError(f"无效的策略 JSON: {e}")

                # 准备参数：先合并所有策略参数，然后添加控制参数
                kwargs = {}
                # 合并策略参数（所有策略参数都可以传入）
                kwargs["strategy"] = strategy_params
                # 添加控制参数
                kwargs["batch_id"] = batch_id
                kwargs["overwrite"] = (
                    overwrite  # overwrite=True 时重建表，overwrite=False 时追加数据
                )

                analyse.run_analyse(task_id=task_id, config_json=json.dumps(kwargs))
                # 检查任务是否被取消
                if check_task(task_id):
                    logger.info(f"任务 {task_id} 已被取消，不标记为成功")
                    log_task_event(task_id, "INFO", "任务被取消")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_CANCELED, "任务被取消"
                    )
                else:
                    logger.info(f"任务 {task_id} 执行成功: 分析数据")
                    log_task_event(task_id, "INFO", "分析数据完成")
                    mark_task_finished(
                        task_id, TaskStatus.TASK_STATUS_SUCCESS, "数据分析完成"
                    )
            except Exception as e:
                logger.error(f"任务 {task_id} 执行失败: {e}")
                log_task_event(task_id, "ERROR", f"分析数据失败: {e}")
                mark_task_finished(task_id, TaskStatus.TASK_STATUS_FAILED, str(e))

        # 在后台线程中启动任务
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # 立即返回运行状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.TASK_STATUS_RUNNING,
        )


def serve():
    """启动 gRPC 服务器"""
    # 创建线程池执行器
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # 绑定服务实现到服务器
    add_TaskServiceServicer_to_server(TaskService(), server)

    # 监听地址和端口
    server.add_insecure_port(f"[::]:{WORKER_PORT}")

    # 启动服务器
    server.start()
    print(f"gRPC Task Service started on port {WORKER_PORT}...")

    # 保持主线程运行，直到服务器停止
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
        print("gRPC Server stopped.")


if __name__ == "__main__":
    serve()
