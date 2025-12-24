import psycopg2
import yaml
from loguru import logger

# 默认配置
with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

db_config = config.get("db", {})


def check_task(task_id: str):
    """
    描述：检查任务是否被取消
    参数：task_id: 任务ID
    返回值：任务是否被取消
    """
    try:
        with psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM tasks WHERE task_id = %s", (str(task_id),)
                )
                result = cursor.fetchone()
                if result is None:
                    logger.error(f"任务 {task_id} 不存在")
                    return True
                return result[0] == "CANCELLED"
    except Exception as e:
        logger.error(f"检查任务 {task_id} 失败: {e}")
        return True


def update_task_status(task_id: str, status: str):
    try:
        with psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE tasks SET status = %s WHERE task_id = %s",
                    (status, str(task_id)),
                )
    except Exception as e:
        logger.error(f"更新任务 {task_id} 状态失败: {e}")


if __name__ == "__main__":
    print(check_task("1"))
