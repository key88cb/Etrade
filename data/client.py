import json
import sys
import time

import grpc

from protos import task_pb2, task_pb2_grpc


def run_task(
    stub,
    task_id: str,
    task_type: str,
    config: dict = None,
    batch_id: str = "",
    experiment_id: str = "",
    trigger: str = "MANUAL",
):
    """提交并启动一个新任务"""
    print(f"\n{'='*60}")
    print(f"Submitting task: {task_id}")
    print(f"Task type: {task_type}")
    print(f"{'='*60}")

    # 构造请求消息
    request = task_pb2.RunTaskRequest(
        task_id=task_id,
        task_type=task_type,
        config_json=json.dumps(config) if config else "",
        batch_id=batch_id,
        experiment_id=experiment_id,
        trigger=trigger,
    )

    try:
        # 调用 RunTask 方法
        response = stub.RunTask(request)

        # 处理响应
        status_name = task_pb2.TaskStatus.Name(response.status)
        print(f"Task submitted successfully!")
        print(f"Status: {status_name}")
        print(f"Log summary: {response.log_summary}")
        print(f"Duration: {response.duration_sec:.2f}s")

        if response.output_metrics:
            print("Output metrics:")
            for key, value in response.output_metrics.items():
                print(f"  {key}: {value}")

        return response

    except grpc.RpcError as e:
        print(f"RPC error occurred: {e.code().name}")
        print(f"Details: {e.details()}")
        return None


def stream_logs(stub, task_id: str):
    """流式接收任务日志"""
    print(f"\n{'='*60}")
    print(f"Streaming logs for task: {task_id}")
    print(f"{'='*60}")

    # 构造请求消息
    request = task_pb2.TaskLogRequest(task_id=task_id)

    try:
        # 调用 StreamLogs 方法（服务器流式 RPC）
        log_stream = stub.StreamLogs(request)

        # 接收并打印日志
        for log_entry in log_stream:
            # 格式化输出日志
            level_color = {
                "INFO": "\033[32m",  # 绿色
                "WARN": "\033[33m",  # 黄色
                "ERROR": "\033[31m",  # 红色
            }.get(log_entry.level, "\033[0m")
            reset_color = "\033[0m"

            print(
                f"{level_color}[{log_entry.timestamp}] {log_entry.level:5s}{reset_color} {log_entry.message}"
            )
            sys.stdout.flush()

    except grpc.RpcError as e:
        print(f"RPC error occurred: {e.code().name}")
        print(f"Details: {e.details()}")


def cancel_task(stub, task_id: str):
    """取消任务"""
    print(f"\n{'='*60}")
    print(f"Canceling task: {task_id}")
    print(f"{'='*60}")

    # 构造请求消息
    request = task_pb2.CancelRequest(task_id=task_id)

    try:
        # 调用 CancelTask 方法
        response = stub.CancelTask(request)

        # 处理响应
        if response.success:
            print(f"✓ Task cancellation requested successfully")
        else:
            print(f"✗ Failed to cancel task: {response.message}")

        return response

    except grpc.RpcError as e:
        print(f"RPC error occurred: {e.code().name}")
        print(f"Details: {e.details()}")
        return None


def run():
    """主函数：演示 TaskService 客户端的使用"""
    # 1. 建立与服务器的连接
    print("Connecting to gRPC server at localhost:50051...")
    with grpc.insecure_channel("localhost:50051") as channel:

        # 2. 创建客户端存根
        stub = task_pb2_grpc.TaskServiceStub(channel)

        # 示例: 提交一个数据导入任务
        task_id_1 = f"task_data_import_{int(time.time())}"
        config_1 = {
            "source": "binance",
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "timeframe": "1h",
        }

        response = run_task(
            stub,
            task_id=task_id_1,
            task_type="DATA_IMPORT",
            config=config_1,
            batch_id="batch_001",
            experiment_id="exp_001",
            trigger="MANUAL",
        )

        if response:
            # 流式接收日志
            stream_logs(stub, task_id_1)

        print("\n" + "=" * 60)
        time.sleep(1)


if __name__ == "__main__":
    run()
