import os
import threading
from concurrent import futures

import grpc
from loguru import logger

# 导入生成的代码
from protos.task_pb2 import TaskResponse, TaskStatus
from protos.task_pb2_grpc import TaskServiceServicer, add_TaskServiceServicer_to_server

# 导入数据收集模块
from block_chain import collect_binance, collect_uniswap


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
