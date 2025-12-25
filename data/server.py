import datetime
import json
import os
import sys
import threading
import time
from concurrent import futures

import grpc
import pika
import pika.exceptions
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
RABBITMQ_CONFIG = CONFIG.get("rabbitmq", {})
WORKER_PORT = str(CONFIG.get("worker_port", 50052))

# 任务队列名称
TASK_QUEUE_NAME = "task_queue"

STATUS_LABELS = {
    TaskStatus.WAIT: "WAIT",
    TaskStatus.RUNNING: "RUNNING",
    TaskStatus.SUCCESS: "SUCCESS",
    TaskStatus.FAILED: "FAILED",
    TaskStatus.CANCELLED: "CANCELLED",
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
    """将任务状态更新为 RUNNING 并设置开始时间"""
    if not task_id:
        return
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks 
                SET status = %s, started_at = COALESCE(started_at, NOW()) 
                WHERE task_id = %s
                """,
                (STATUS_LABELS.get(TaskStatus.RUNNING), task_id),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("更新任务开始时间和状态失败: %s", exc)


def mark_task_waiting(task_id: str):
    """将任务状态设置为 WAIT"""
    if not task_id:
        return
    try:
        with _get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET status = %s WHERE task_id = %s",
                (STATUS_LABELS.get(TaskStatus.WAIT), task_id),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("更新任务状态为 WAIT 失败: %s", exc)


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


class RabbitMQManager:
    """RabbitMQ 连接和队列管理器（线程安全）"""

    def __init__(self):
        self._publish_connection = None
        self._publish_channel = None
        self._publish_lock = threading.Lock()
        self._consume_connection = None
        self._consume_channel = None

    def _get_connection_parameters(self):
        """获取连接参数"""
        username = str(RABBITMQ_CONFIG.get("username", "guest"))
        password = str(RABBITMQ_CONFIG.get("password", "guest"))
        credentials = pika.PlainCredentials(username, password)
        return pika.ConnectionParameters(
            host=RABBITMQ_CONFIG.get("host", "localhost"),
            port=int(RABBITMQ_CONFIG.get("port", 5672)),
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

    def connect(self):
        """连接到 RabbitMQ 服务器（初始化发布连接）"""
        try:
            parameters = self._get_connection_parameters()
            self._publish_connection = pika.BlockingConnection(parameters)
            self._publish_channel = self._publish_connection.channel()
            # 声明队列（持久化）
            self._publish_channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
            logger.info("RabbitMQ 发布连接成功")
        except Exception as e:
            logger.error(f"RabbitMQ 连接失败: {e}")
            raise

    def connect_consume(self):
        """创建用于消费的独立连接（线程安全）"""
        try:
            parameters = self._get_connection_parameters()
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            # 声明队列（持久化）
            channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)
            return connection, channel
        except Exception as e:
            logger.error(f"创建消费连接失败: {e}")
            raise

    def _ensure_publish_connection(self):
        """确保发布连接可用"""
        if not self._publish_connection or self._publish_connection.is_closed:
            parameters = self._get_connection_parameters()
            self._publish_connection = pika.BlockingConnection(parameters)
            self._publish_channel = self._publish_connection.channel()
            self._publish_channel.queue_declare(queue=TASK_QUEUE_NAME, durable=True)

    def publish_task(self, task_type: str, task_data: dict):
        """发布任务到队列（线程安全）"""
        with self._publish_lock:
            try:
                self._ensure_publish_connection()

                message = {
                    "task_type": task_type,
                    "task_data": task_data,
                }
                self._publish_channel.basic_publish(
                    exchange="",
                    routing_key=TASK_QUEUE_NAME,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 使消息持久化
                    ),
                )
                logger.info(f"任务已入队: task_type={task_type}, task_id={task_data.get('task_id')}")
            except Exception as e:
                logger.error(f"发布任务到队列失败: {e}")
                # 尝试重新连接
                try:
                    self._ensure_publish_connection()
                    # 重试一次
                    self._publish_channel.basic_publish(
                        exchange="",
                        routing_key=TASK_QUEUE_NAME,
                        body=json.dumps(message),
                        properties=pika.BasicProperties(delivery_mode=2),
                    )
                    logger.info(f"任务已入队（重试成功）: task_type={task_type}, task_id={task_data.get('task_id')}")
                except Exception as retry_err:
                    logger.error(f"发布任务重试失败: {retry_err}")
                    raise

    def close(self):
        """关闭所有连接"""
        try:
            if self._publish_connection and not self._publish_connection.is_closed:
                self._publish_connection.close()
        except Exception:
            pass


# 全局 RabbitMQ 管理器实例
rabbitmq_manager = RabbitMQManager()

# 任务执行线程池（支持5个任务并发执行）
task_executor = futures.ThreadPoolExecutor(max_workers=5)


def execute_task(task_type: str, task_data: dict):
    """执行任务的通用函数"""
    task_id = task_data.get("task_id")
    if not task_id:
        logger.error("任务 ID 不能为空")
        return

    try:
        logger.info(f"开始执行任务 {task_id}: {task_type}")
        mark_task_started(task_id)
        log_task_event(task_id, "INFO", f"开始执行任务: {task_type}")

        if task_type == "collect_binance":
            csv_path = os.path.join(os.path.dirname(__file__), "ETHUSDT-trades-2025-09.csv")
            collect_binance.collect_binance(
                task_id=task_id,
                csv_path=csv_path,
                import_percentage=task_data.get("import_percentage", 100),
                chunk_size=task_data.get("chunk_size", 1000000),
            )
            success_msg = "Binance 数据导入完成"
            log_msg = "收集 Binance 数据完成"

        elif task_type == "collect_binance_by_date":
            collect_binance.collect_binance_by_date(
                task_id=task_id,
                start_ts=task_data.get("start_ts"),
                end_ts=task_data.get("end_ts"),
            )
            success_msg = "Binance 数据按日期收集完成"
            log_msg = "按日期收集 Binance 数据完成"

        elif task_type == "collect_uniswap":
            collect_uniswap.collect_uniswap(
                task_id=task_id,
                pool_address=task_data.get("pool_address"),
                start_ts=task_data.get("start_ts"),
                end_ts=task_data.get("end_ts"),
            )
            success_msg = "Uniswap 数据采集完成"
            log_msg = "收集 Uniswap 数据完成"

        elif task_type == "process_prices":
            # 将时间戳转换为日期字符串
            start_date_str = None
            end_date_str = None
            if task_data.get("start_date"):
                dt = datetime.datetime.fromtimestamp(
                    task_data.get("start_date"), tz=datetime.timezone.utc
                )
                start_date_str = dt.isoformat()
            if task_data.get("end_date"):
                dt = datetime.datetime.fromtimestamp(
                    task_data.get("end_date"), tz=datetime.timezone.utc
                )
                end_date_str = dt.isoformat()

            kwargs = {
                "aggregation_interval": task_data.get("aggregation_interval", "minute"),
                "overwrite": task_data.get("overwrite", False),
                "start_date": start_date_str,
                "end_date": end_date_str,
            }
            # 合并 db_overrides
            db_overrides = task_data.get("db_overrides", {})
            if db_overrides:
                kwargs.update(db_overrides)

            process_prices.run_process_prices(task_id=task_id, **kwargs)
            success_msg = "价格数据处理完成"
            log_msg = "处理价格数据完成"

        elif task_type == "analyse":
            # 解析策略参数
            strategy_params = task_data.get("strategy_params", {})
            kwargs = {
                "strategy": strategy_params,
                "batch_id": task_data.get("batch_id"),
                "overwrite": task_data.get("overwrite", False),
            }
            analyse.run_analyse(task_id=task_id, config_json=json.dumps(kwargs))
            success_msg = "数据分析完成"
            log_msg = "分析数据完成"

        else:
            raise ValueError(f"未知的任务类型: {task_type}")

        # 检查任务是否被取消
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已被取消")
            log_task_event(task_id, "INFO", "任务被取消")
            mark_task_finished(task_id, TaskStatus.CANCELLED, "任务被取消")
        else:
            logger.info(f"任务 {task_id} 执行成功: {task_type}")
            log_task_event(task_id, "INFO", log_msg)
            mark_task_finished(task_id, TaskStatus.SUCCESS, success_msg)

    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {e}")
        log_task_event(task_id, "ERROR", f"任务执行失败: {e}")
        mark_task_finished(task_id, TaskStatus.FAILED, str(e))


def consume_tasks():
    """从队列中消费任务并并发执行（支持5个任务并发）"""
    def callback(ch, method, properties, body):
        try:
            message = json.loads(body)
            task_type = message.get("task_type")
            task_data = message.get("task_data")

            if not task_type or not task_data:
                logger.error(f"无效的任务消息: {message}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # 在线程池中异步执行任务
            # 注意：我们在任务提交到线程池后立即确认消息
            # 因为任务状态已经在数据库中记录，即使任务失败也不应该重复处理
            task_executor.submit(execute_task, task_type, task_data)
            
            # 立即确认消息（任务已提交到线程池，状态会在数据库中记录）
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"处理队列消息失败: {e}")
            # 发生异常时立即确认消息，避免重复处理
            try:
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                pass

    # 持续监听队列
    while True:
        connection = None
        channel = None
        try:
            # 创建独立的消费连接（与发布连接分离，保证线程安全）
            connection, channel = rabbitmq_manager.connect_consume()
            
            # 设置 QoS，每个消费者可以预取5个任务，支持并发执行
            channel.basic_qos(prefetch_count=5)
            # 开始消费
            channel.basic_consume(
                queue=TASK_QUEUE_NAME,
                on_message_callback=callback,
            )

            logger.info("开始监听任务队列（支持5个任务并发执行）...")
            # start_consuming() 会阻塞，直到连接关闭或出现异常
            channel.start_consuming()
        except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
            logger.warning(f"RabbitMQ 消费连接关闭: {e}，5秒后重试...")
            try:
                if connection and not connection.is_closed:
                    connection.close()
            except Exception:
                pass
            time.sleep(5)
        except Exception as e:
            logger.error(f"消费任务时出错: {e}，5秒后重试...")
            try:
                if connection and not connection.is_closed:
                    connection.close()
            except Exception:
                pass
            time.sleep(5)


class TaskService(TaskServiceServicer):
    """实现 TaskService 的 gRPC 服务"""

    def CollectBinance(self, request, context):
        """
        收集币安数据
        将任务放入队列，立即返回等待状态
        """
        task_id = request.task_id
        import_percentage = request.import_percentage
        chunk_size = request.chunk_size

        logger.info(
            f"收到收集币安数据请求: task_id={task_id}, "
            f"import_percentage={import_percentage}, chunk_size={chunk_size}"
        )

        # 将任务状态设置为 WAIT
        mark_task_waiting(task_id)
        log_task_event(task_id, "INFO", "任务已入队，等待执行")

        # 将任务放入队列
        task_data = {
            "task_id": task_id,
            "import_percentage": import_percentage,
            "chunk_size": chunk_size,
        }
        try:
            rabbitmq_manager.publish_task("collect_binance", task_data)
        except Exception as e:
            logger.error(f"将任务放入队列失败: {e}")
            mark_task_finished(task_id, TaskStatus.FAILED, f"任务入队失败: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
            )

        # 返回等待状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.WAIT,
        )

    def CollectBinanceByDate(self, request, context):
        """
        按日期收集币安数据
        将任务放入队列，立即返回等待状态
        """
        task_id = request.task_id
        start_ts = request.start_ts
        end_ts = request.end_ts

        logger.info(
            f"收到按日期收集币安数据请求: task_id={task_id}, "
            f"start_ts={start_ts}, end_ts={end_ts}"
        )

        # 将任务状态设置为 WAIT
        mark_task_waiting(task_id)
        log_task_event(task_id, "INFO", "任务已入队，等待执行")

        # 将任务放入队列
        task_data = {
            "task_id": task_id,
            "start_ts": start_ts,
            "end_ts": end_ts,
        }
        try:
            rabbitmq_manager.publish_task("collect_binance_by_date", task_data)
        except Exception as e:
            logger.error(f"将任务放入队列失败: {e}")
            mark_task_finished(task_id, TaskStatus.FAILED, f"任务入队失败: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
            )

        # 返回等待状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.WAIT,
        )

    def CollectUniswap(self, request, context):
        """
        收集 Uniswap 数据
        将任务放入队列，立即返回等待状态
        """
        task_id = request.task_id
        pool_address = request.pool_address
        start_ts = request.start_ts
        end_ts = request.end_ts

        logger.info(
            f"收到收集 Uniswap 数据请求: task_id={task_id}, "
            f"pool_address={pool_address}, start_ts={start_ts}, end_ts={end_ts}"
        )

        # 将任务状态设置为 WAIT
        mark_task_waiting(task_id)
        log_task_event(task_id, "INFO", "任务已入队，等待执行")

        # 将任务放入队列
        task_data = {
            "task_id": task_id,
            "pool_address": pool_address,
            "start_ts": start_ts,
            "end_ts": end_ts,
        }
        try:
            rabbitmq_manager.publish_task("collect_uniswap", task_data)
        except Exception as e:
            logger.error(f"将任务放入队列失败: {e}")
            mark_task_finished(task_id, TaskStatus.FAILED, f"任务入队失败: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
            )

        # 返回等待状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.WAIT,
        )

    def ProcessPrices(self, request, context):
        """
        处理价格数据
        将任务放入队列，立即返回等待状态
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

        # 将任务状态设置为 WAIT
        mark_task_waiting(task_id)
        log_task_event(task_id, "INFO", "任务已入队，等待执行")

        # 将任务放入队列
        task_data = {
            "task_id": task_id,
            "start_date": start_date,
            "end_date": end_date,
            "aggregation_interval": aggregation_interval,
            "overwrite": overwrite,
            "db_overrides": db_overrides,
        }
        try:
            rabbitmq_manager.publish_task("process_prices", task_data)
        except Exception as e:
            logger.error(f"将任务放入队列失败: {e}")
            mark_task_finished(task_id, TaskStatus.FAILED, f"任务入队失败: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
            )

        # 返回等待状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.WAIT,
        )

    def Analyse(self, request, context):
        """
        分析数据
        将任务放入队列，立即返回等待状态
        """
        task_id = request.task_id
        batch_id = request.batch_id
        overwrite = request.overwrite
        strategy_json = request.strategy_json

        logger.info(
            f"收到分析数据请求: task_id={task_id}, "
            f"batch_id={batch_id}, overwrite={overwrite}"
        )

        # 解析策略 JSON
        strategy_params = {}
        if strategy_json:
            try:
                strategy_params = json.loads(strategy_json)
            except json.JSONDecodeError as e:
                logger.error(f"解析策略 JSON 失败: {e}")
                mark_task_finished(task_id, TaskStatus.FAILED, f"无效的策略 JSON: {e}")
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                )

        # 将任务状态设置为 WAIT
        mark_task_waiting(task_id)
        log_task_event(task_id, "INFO", "任务已入队，等待执行")

        # 将任务放入队列
        task_data = {
            "task_id": task_id,
            "batch_id": batch_id,
            "overwrite": overwrite,
            "strategy_params": strategy_params,
        }
        try:
            rabbitmq_manager.publish_task("analyse", task_data)
        except Exception as e:
            logger.error(f"将任务放入队列失败: {e}")
            mark_task_finished(task_id, TaskStatus.FAILED, f"任务入队失败: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
            )

        # 返回等待状态
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.WAIT,
        )


def serve():
    """启动 gRPC 服务器和 RabbitMQ 消费者"""
    # 初始化 RabbitMQ 连接
    try:
        rabbitmq_manager.connect()
        logger.info("RabbitMQ 连接初始化成功")
    except Exception as e:
        logger.error(f"RabbitMQ 连接初始化失败: {e}")
        logger.warning("继续启动 gRPC 服务器，但任务队列功能可能不可用")

    # 启动消费者线程（后台线程）
    consumer_thread = threading.Thread(target=consume_tasks, daemon=True)
    consumer_thread.start()
    logger.info("任务消费者线程已启动")

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
        logger.info("正在关闭服务器...")
        server.stop(0)
        # 关闭任务执行线程池
        task_executor.shutdown(wait=True)
        rabbitmq_manager.close()
        print("gRPC Server stopped.")


if __name__ == "__main__":
    serve()
