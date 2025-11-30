import psycopg2
import yaml

# 默认配置
with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

db_config = config.get("db", {})

def check_task(task_id: str):
    """
    描述：检查任务是否被取消
    参数：task_id: 任务ID
    返回值：任务是否存在
    """
    with psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["database"],
        user=db_config["username"],
        password=db_config["password"],
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM task_results WHERE task_id = %s", (str(task_id),))
            return cursor.fetchone()[0] == 3 # TASK_STATUS_CANCELED

def update_task_status(task_id: str, status: int):
    with psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["database"],
        user=db_config["username"],
        password=db_config["password"],
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE tasks SET status = %s WHERE task_id = %s", (status, str(task_id)))

if __name__ == "__main__":
    print(check_task("1"))
    print(check_task("2"))
    update_task_status("1", 1)
    print(check_task("1"))
    update_task_status("1", 3)
    print(check_task("1"))