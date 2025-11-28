import datetime
import json
import os
import threading
from concurrent import futures

import grpc
from loguru import logger

# 导入生成的代码
from protos.task_pb2 import TaskResponse, TaskStatus
from protos.task_pb2_grpc import TaskServiceServicer, add_TaskServiceServicer_to_server

# 导入数据收集模块
from block_chain import collect_binance, collect_uniswap, process_prices, analyse


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
        csv_path = os.path.join(
            os.path.dirname(__file__), 
            "ETHUSDT-trades-2025-09.csv"
        )

        def run_task():
            """在后台线程中执行任务"""
            try:
                logger.info(f"开始执行任务 {task_id}: 收集币安数据")
                collect_binance.collect_binance(
                    task_id=task_id,
                    csv_path=csv_path,
                    import_percentage=import_percentage,
                    chunk_size=chunk_size,
                )
                logger.info(f"任务 {task_id} 执行成功: 收集币安数据")
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
                collect_uniswap.collect_uniswap(
                    task_id=task_id,
                    pool_address=pool_address,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                logger.info(f"任务 {task_id} 执行成功: 收集 Uniswap 数据")
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
                    dt = datetime.datetime.fromtimestamp(start_date, tz=datetime.timezone.utc)
                    start_date_str = dt.strftime("%Y-%m-%d")
                
                if end_date:
                    dt = datetime.datetime.fromtimestamp(end_date, tz=datetime.timezone.utc)
                    end_date_str = dt.strftime("%Y-%m-%d")
                
                # 准备参数
                kwargs = {
                    "aggregation_interval": aggregation_interval if aggregation_interval else "minute",
                    "overwrite": overwrite,
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                }
                
                # 合并 db_overrides（如果有）
                if db_overrides:
                    kwargs.update(db_overrides)
                
                process_prices.run_process_prices(
                    task_id=task_id,
                    **kwargs
                )
                logger.info(f"任务 {task_id} 执行成功: 处理价格数据")
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
                kwargs.update(strategy_params)
                # 添加控制参数
                kwargs["batch_id"] = batch_id
                kwargs["overwrite"] = overwrite  # overwrite=True 时重建表，overwrite=False 时追加数据
                
                analyse.run_analyse(
                    task_id=task_id,
                    **kwargs
                )
                logger.info(f"任务 {task_id} 执行成功: 分析数据")
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


def serve():
    """启动 gRPC 服务器"""
    # 创建线程池执行器
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # 绑定服务实现到服务器
    add_TaskServiceServicer_to_server(TaskService(), server)

    # 监听地址和端口
    server.add_insecure_port("[::]:50051")

    # 启动服务器
    server.start()
    print("gRPC Task Service started on port 50051...")

    # 保持主线程运行，直到服务器停止
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
        print("gRPC Server stopped.")


if __name__ == "__main__":
    serve()
