import grpc
import time
import json
import threading
from datetime import datetime
from concurrent import futures
from typing import Dict, List, Optional
from queue import Queue, Empty

# 导入生成的代码
from protos import task_pb2, task_pb2_grpc


class TaskManager:
    """任务管理器，负责管理任务状态和日志"""
    
    def __init__(self):
        self._lock = threading.Lock()
        # 存储任务信息: task_id -> {status, start_time, end_time, logs, cancel_flag, output_metrics}
        self._tasks: Dict[str, Dict] = {}
        # 存储任务日志: task_id -> Queue of TaskLog
        self._task_logs: Dict[str, Queue] = {}
    
    def create_task(self, task_id: str, task_type: str, config_json: str, 
                   batch_id: str, experiment_id: str, trigger: str) -> bool:
        """创建新任务"""
        with self._lock:
            if task_id in self._tasks:
                return False  # 任务已存在
            
            self._tasks[task_id] = {
                'task_id': task_id,
                'task_type': task_type,
                'config_json': config_json,
                'batch_id': batch_id,
                'experiment_id': experiment_id,
                'trigger': trigger,
                'status': task_pb2.TASK_STATUS_QUEUED,
                'start_time': None,
                'end_time': None,
                'cancel_flag': threading.Event(),
                'output_metrics': {},
                'thread': None
            }
            self._task_logs[task_id] = Queue()
            return True
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: int):
        """更新任务状态"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]['status'] = status
                if status == task_pb2.TASK_STATUS_RUNNING and self._tasks[task_id]['start_time'] is None:
                    self._tasks[task_id]['start_time'] = time.time()
                elif status in [task_pb2.TASK_STATUS_SUCCESS, task_pb2.TASK_STATUS_FAILED, 
                               task_pb2.TASK_STATUS_CANCELED]:
                    self._tasks[task_id]['end_time'] = time.time()
    
    def add_log(self, task_id: str, level: str, message: str):
        """添加任务日志"""
        timestamp = datetime.now().isoformat()
        log_entry = task_pb2.TaskLog(
            timestamp=timestamp,
            level=level,
            message=message
        )
        if task_id in self._task_logs:
            self._task_logs[task_id].put(log_entry)
    
    def get_logs(self, task_id: str) -> Queue:
        """获取任务日志队列"""
        with self._lock:
            return self._task_logs.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task['status'] in [task_pb2.TASK_STATUS_QUEUED, task_pb2.TASK_STATUS_RUNNING]:
                    task['cancel_flag'].set()
                    self.update_task_status(task_id, task_pb2.TASK_STATUS_CANCELED)
                    self.add_log(task_id, "INFO", f"Task {task_id} cancellation requested")
                    return True
        return False
    
    def set_output_metrics(self, task_id: str, metrics: Dict[str, str]):
        """设置任务输出指标"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]['output_metrics'].update(metrics)


# 全局任务管理器实例
task_manager = TaskManager()


def execute_task(task_id: str, task_type: str, config_json: str):
    """执行任务的函数（在后台线程中运行）"""
    try:
        # 更新状态为运行中
        task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_RUNNING)
        task_manager.add_log(task_id, "INFO", f"Task {task_id} started")
        task_manager.add_log(task_id, "INFO", f"Task type: {task_type}")
        
        # 解析配置
        try:
            config = json.loads(config_json) if config_json else {}
            task_manager.add_log(task_id, "INFO", f"Config loaded: {json.dumps(config)}")
        except json.JSONDecodeError:
            task_manager.add_log(task_id, "WARN", f"Invalid JSON config, using empty config")
            config = {}
        
        # 检查是否被取消
        task = task_manager.get_task(task_id)
        if task and task['cancel_flag'].is_set():
            task_manager.add_log(task_id, "INFO", f"Task {task_id} was canceled before execution")
            task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_CANCELED)
            return
        
        # 模拟任务执行（这里可以根据 task_type 执行不同的任务）
        task_manager.add_log(task_id, "INFO", f"Executing task logic for type: {task_type}")
        
        # 示例：根据任务类型执行不同的逻辑
        if task_type == "DATA_IMPORT":
            # 模拟数据导入
            task = task_manager.get_task(task_id)
            if task and task['cancel_flag'].is_set():
                task_manager.add_log(task_id, "WARN", f"Task {task_id} canceled during execution")
                task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_CANCELED)
                return
            time.sleep(0.5)
            
            task_manager.set_output_metrics(task_id, {
                "imported_rows": "1000",
                "files_processed": "5"
            })
            task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_SUCCESS)
            task_manager.add_log(task_id, "INFO", f"Task {task_id} completed successfully")
            
        elif task_type == "REPORT_GEN":
            # 模拟报告生成
            task = task_manager.get_task(task_id)
            if task and task['cancel_flag'].is_set():
                task_manager.add_log(task_id, "WARN", f"Task {task_id} canceled during execution")
                task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_CANCELED)
                return
            time.sleep(0.3)
            
            task_manager.set_output_metrics(task_id, {
                "report_file_path": "/tmp/report.pdf",
                "pages": "10"
            })
            task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_SUCCESS)
            task_manager.add_log(task_id, "INFO", f"Task {task_id} completed successfully")
            
        else:
            # 默认任务执行
            time.sleep(1)
            task = task_manager.get_task(task_id)
            if task and task['cancel_flag'].is_set():
                task_manager.add_log(task_id, "WARN", f"Task {task_id} canceled during execution")
                task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_CANCELED)
                return
            
            task_manager.set_output_metrics(task_id, {
                "result": "completed",
                "task_type": task_type
            })
            task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_SUCCESS)
            task_manager.add_log(task_id, "INFO", f"Task {task_id} completed successfully")
            
    except Exception as e:
        task_manager.update_task_status(task_id, task_pb2.TASK_STATUS_FAILED)
        task_manager.add_log(task_id, "ERROR", f"Task {task_id} failed: {str(e)}")


class TaskService(task_pb2_grpc.TaskServiceServicer):
    """TaskService 服务的实现"""

    def RunTask(self, request, context):
        """提交并启动一个新任务"""
        task_id = request.task_id
        
        # 检查任务是否已存在
        if task_manager.get_task(task_id) is not None:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(f"Task {task_id} already exists")
            return task_pb2.RunTaskResponse(
                status=task_pb2.TASK_STATUS_UNSPECIFIED,
                duration_sec=0.0,
                log_summary="Task already exists"
            )
        
        # 创建任务
        if not task_manager.create_task(
            task_id=task_id,
            task_type=request.task_type,
            config_json=request.config_json,
            batch_id=request.batch_id,
            experiment_id=request.experiment_id,
            trigger=request.trigger
        ):
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to create task")
            return task_pb2.RunTaskResponse(
                status=task_pb2.TASK_STATUS_UNSPECIFIED,
                duration_sec=0.0,
                log_summary="Failed to create task"
            )
        
        # 在后台线程中执行任务
        task = task_manager.get_task(task_id)
        thread = threading.Thread(
            target=execute_task,
            args=(task_id, request.task_type, request.config_json),
            daemon=True
        )
        thread.start()
        task['thread'] = thread
        
        # 立即返回，任务在后台执行
        return task_pb2.RunTaskResponse(
            status=task_pb2.TASK_STATUS_QUEUED,
            duration_sec=0.0,
            log_summary=f"Task {task_id} queued for execution"
        )

    def StreamLogs(self, request, context):
        """通过服务器流式 RPC 实时推送特定任务的执行日志"""
        task_id = request.task_id
        log_queue = task_manager.get_logs(task_id)
        
        if log_queue is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Task {task_id} not found")
            return
        
        # 发送已有的日志
        while True:
            try:
                # 非阻塞获取日志
                log_entry = log_queue.get(timeout=0.1)
                yield log_entry
            except Empty:
                # 检查任务是否还在运行
                task = task_manager.get_task(task_id)
                if task is None:
                    break
                
                status = task['status']
                # 如果任务已完成或失败，发送剩余日志后退出
                if status in [task_pb2.TASK_STATUS_SUCCESS, task_pb2.TASK_STATUS_FAILED, 
                             task_pb2.TASK_STATUS_CANCELED]:
                    # 再尝试一次获取日志
                    try:
                        while True:
                            log_entry = log_queue.get_nowait()
                            yield log_entry
                    except Empty:
                        pass
                    break
                
                # 如果连接被关闭，退出
                if context.is_active():
                    continue
                else:
                    break

    def CancelTask(self, request, context):
        """尝试取消一个正在执行或排队中的任务"""
        task_id = request.task_id
        
        if task_manager.cancel_task(task_id):
            return task_pb2.CancelResponse(
                success=True,
                message=f"Task {task_id} cancellation requested"
            )
        else:
            task = task_manager.get_task(task_id)
            if task is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return task_pb2.CancelResponse(
                    success=False,
                    message=f"Task {task_id} not found"
                )
            else:
                return task_pb2.CancelResponse(
                    success=False,
                    message=f"Task {task_id} cannot be canceled (status: {task['status']})"
                )


def serve():
    """启动 gRPC 服务器"""
    # 创建线程池执行器
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # 绑定服务实现到服务器
    task_pb2_grpc.add_TaskServiceServicer_to_server(TaskService(), server)
    
    # 监听地址和端口
    server.add_insecure_port('[::]:50051')
    
    # 启动服务器
    server.start()
    print("gRPC Task Service started on port 50051...")
    
    # 保持主线程运行，直到服务器停止
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
        print("gRPC Server stopped.")


if __name__ == '__main__':
    serve()