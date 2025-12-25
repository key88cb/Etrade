import time
from typing import Any, Iterable, Optional

import pandas as pd
import psycopg2
import requests
import yaml
from loguru import logger
from psycopg2.extras import execute_values

from .task import check_task, update_task_status

with open("./config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

db_config = config.get("db", {})
graph_config = config.get("the_graph", {})


def fetch_all_swaps(task_id: str, pool_address: str, start_ts: int, end_ts: int):
    """
    描述：通过分页获取指定时间范围内的所有Swap数据。
    参数：
        pool_address：池地址
        start_ts：起始时间的Unix时间戳（秒级）
        end_ts：终止时间的Unix时间戳（秒级）
    返回值：获取到的uniswap数据
    """
    all_swaps = []
    last_id = ""
    logger.info(f"开始从 The Graph 获取 Uniswap 数据，范围 {start_ts} - {end_ts}")
    query_template = """
    query GetRecentSwaps {{
      swaps(
        first: 1000,
        orderBy: id
        orderDirection: asc
        where: {{
          pool: "{pool}"
          timestamp_gte: {start}
          timestamp_lte: {end}
          id_gt: "{last_id}"
        }}
      ) {{
        id
        timestamp
        amount0
        amount1
        transaction {{
          id
          gasPrice
        }}
      }}
    }}
    """
    headers = {
        "Authorization": f"Bearer {graph_config['api_key']}",
        "Content-Type": "application/json",
    }
    retry_count = 0
    while retry_count < 3:
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，停止获取 Uniswap 数据")
            break
        query = query_template.format(
            pool=pool_address, start=start_ts, end=end_ts, last_id=last_id
        )
        try:
            response = requests.post(
                graph_config["graph_api_url"],
                json={"query": query},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            swaps = response.json()["data"]["swaps"]
        except (requests.exceptions.RequestException, KeyError) as exc:
            logger.warning("请求失败: %s，5秒后重试...", exc)
            retry_count += 1
            time.sleep(5)
            continue
        if not swaps:
            break
        retry_count = 0
        all_swaps.extend(swaps)
        last_id = swaps[-1]["id"]
        logger.info(f"目前累计获取 {len(all_swaps)} 条记录...")
    return all_swaps


def process_and_store_uniswap_data(
    task_id: str, swaps_data: Iterable[dict[str, Any]], conn: Optional[Any] = None
) -> int:
    """
    描述：处理数据并存入数据库。
    参数：
        task_id: 任务ID
        swaps_data: Uniswap数据
        conn: 数据库连接（可选），如果提供则使用该连接，否则创建新连接
    返回值：写入的记录数量
    """
    swaps = list(swaps_data)
    if not swaps:
        logger.info("没有获取到 Uniswap 数据。")
        return 0

    logger.info(f"正在处理 {len(swaps)} 条 Uniswap 数据...")
    records = []
    for s in swaps:
        amount0 = float(s["amount0"])
        amount1 = float(s["amount1"])
        if amount0 == 0:
            continue
        price = abs(amount1 / amount0)
        records.append(
            (
                pd.to_datetime(
                    pd.to_numeric(s["timestamp"], errors="coerce"), unit="s", utc=True
                ).to_pydatetime(),
                price,
                amount0,
                amount1,
                int(s["transaction"]["gasPrice"]),
                s["transaction"]["id"],
            )
        )

    if not records:
        logger.info("没有可写入的数据。")
        return 0

    # 如果提供了连接，使用它；否则创建新连接
    if conn is not None:
        with conn.cursor() as cur:
            insert_sql = """
            INSERT INTO uniswap_swaps (block_time, price, amount_eth, amount_usdt, gas_price, tx_hash)
            VALUES %s
            """
            execute_values(cur, insert_sql, records, page_size=1000)
        # 不在这里提交，由调用者控制事务
    else:
        with psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        ) as new_conn, new_conn.cursor() as cur:
            insert_sql = """
            INSERT INTO uniswap_swaps (block_time, price, amount_eth, amount_usdt, gas_price, tx_hash)
            VALUES %s
            """
            execute_values(cur, insert_sql, records, page_size=1000)
    logger.info(f"成功写入 {len(records)} 条 Uniswap 记录。")
    return len(records)


def collect_uniswap(task_id: str, pool_address: str, start_ts: int, end_ts: int) -> int:
    """
    描述：收集 Uniswap 数据（作为事务处理，如果任务取消则完全回滚）
    参数：
        task_id: 任务ID
        pool_address: 池地址
        start_ts: 起始时间戳（秒级）
        end_ts: 终止时间戳（秒级）
    返回值：导入的总行数
    """
    conn = None
    try:
        # 创建数据库连接并开始事务
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            dbname=db_config["database"],
            user=db_config["username"],
            password=db_config["password"],
        )
        conn.autocommit = False  # 禁用自动提交，使用事务
        logger.info("已开启数据库事务，所有导入操作将在事务中执行")

        swaps = fetch_all_swaps(task_id, pool_address, start_ts, end_ts)
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，回滚所有已导入的数据")
            conn.rollback()
            logger.info("已回滚所有数据")
            return 0

        rows_counter = process_and_store_uniswap_data(task_id, swaps, conn)
        
        if check_task(task_id):
            logger.info(f"任务 {task_id} 已取消，回滚所有已导入的数据")
            conn.rollback()
            logger.info("已回滚所有数据")
            return 0

        # 所有数据导入成功，提交事务
        conn.commit()
        logger.info("事务已提交，所有数据已成功导入")
        update_task_status(task_id, "SUCCESS")
        return rows_counter
    except Exception as e:
        logger.error(f"获取Uniswap数据失败: {e}")
        # 确保在异常情况下回滚事务
        if conn is not None:
            try:
                conn.rollback()
                logger.info("发生异常，已回滚所有数据")
            except Exception as rollback_error:
                logger.error(f"回滚事务失败: {rollback_error}")
        update_task_status(task_id, "FAILED")
        return 0
    finally:
        # 确保关闭数据库连接
        if conn is not None:
            try:
                conn.close()
            except Exception as close_error:
                logger.warning(f"关闭数据库连接失败: {close_error}")


if __name__ == "__main__":
    collect_uniswap(
        1, "0x11b815efb8f581194ae79006d24e0d814b7697f6", 1756684800, 1756771200
    )
