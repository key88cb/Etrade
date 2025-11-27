import argparse
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import pandas as pd
import psycopg2
import requests
import yaml
from loguru import logger
from psycopg2.extras import execute_values
from .task_client import TaskClient, load_config_from_string

with open("config/config.yaml", "r", encoding="utf-8") as file:
    _CONFIG = yaml.safe_load(file)

DEFAULT_DB_CONFIG = _CONFIG.get("db", {})
DEFAULT_GRAPH_CONFIG = _CONFIG.get("the_graph", {})


def fetch_all_swaps(
    graph_api_url: str, api_key: str, pool_address: str, start_ts: int, end_ts: int
):
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
    logger.info("开始从 The Graph 获取 Uniswap 数据，范围 %s - %s", start_ts, end_ts)
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
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    while True:
        query = query_template.format(
            pool=pool_address, start=start_ts, end=end_ts, last_id=last_id
        )
        try:
            response = requests.post(
                graph_api_url, json={"query": query}, headers=headers, timeout=30
            )
            response.raise_for_status()
            swaps = response.json()["data"]["swaps"]
        except (requests.exceptions.RequestException, KeyError) as exc:
            logger.warning("请求失败: %s，5秒后重试...", exc)
            time.sleep(5)
            continue
        if not swaps:
            break
        all_swaps.extend(swaps)
        last_id = swaps[-1]["id"]
        logger.info("目前累计获取 %s 条记录...", len(all_swaps))
    return all_swaps


def process_and_store_uniswap_data(swaps_data: Iterable[dict[str, Any]], conn) -> int:
    """
    描述：处理数据并存入数据库。
    返回值：写入的记录数量
    """
    swaps = list(swaps_data)
    if not swaps:
        logger.info("没有获取到 Uniswap 数据。")
        return 0

    logger.info("正在处理 %s 条 Uniswap 数据...", len(swaps))
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

    with conn, conn.cursor() as cur:
        insert_sql = """
        INSERT INTO uniswap_swaps (block_time, price, amount_eth, amount_usdt, gas_price, tx_hash)
        VALUES %s
        """
        execute_values(cur, insert_sql, records, page_size=1000)
    logger.info("成功写入 %s 条 Uniswap 记录。", len(records))
    return len(records)


def _build_db_conn(overrides: dict[str, Any]):
    cfg = DEFAULT_DB_CONFIG.copy()
    cfg.update(overrides or {})
    return psycopg2.connect(
        dbname=cfg.get("database"),
        user=cfg.get("username"),
        password=cfg.get("password"),
        host=cfg.get("host"),
        port=cfg.get("port"),
    )


def _iter_days(start: datetime, end: datetime):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def run_collect_uniswap(
    task_id: Optional[str] = None, config_json: Optional[str] = None
):
    config = load_config_from_string(config_json)
    client = TaskClient(task_id)
    graph_cfg = DEFAULT_GRAPH_CONFIG.copy()
    graph_cfg.update(config.get("the_graph", {}))

    start_date = config.get("start_date")
    end_date = config.get("end_date")

    if start_date:
        start_dt = datetime.fromisoformat(start_date).astimezone(timezone.utc)
    else:
        start_dt = datetime.now(tz=timezone.utc) - timedelta(days=1)
    if end_date:
        end_dt = datetime.fromisoformat(end_date).astimezone(timezone.utc)
    else:
        end_dt = start_dt
    if end_dt < start_dt:
        raise ValueError("end_date 必须不早于 start_date")

    client.update_status(
        "running", f"开始抓取 {start_dt.date()} - {end_dt.date()} 的 Uniswap 数据"
    )

    conn = _build_db_conn(config.get("db", {}))
    total_written = 0
    try:
        for day in _iter_days(start_dt.date(), end_dt.date()):
            day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
            logger.info("正在处理日期 %s", day_start.date())
            swaps = fetch_all_swaps(
                graph_cfg["graph_api_url"],
                graph_cfg["api_key"],
                graph_cfg["uniswap_pool_address"],
                int(day_start.timestamp()),
                int(day_end.timestamp()),
            )
            written = process_and_store_uniswap_data(swaps, conn)
            total_written += written
    except Exception as exc:
        client.update_status("failed", f"抓取失败: {exc}")
        raise
    else:
        client.update_status(
            "success",
            f"抓取完成，共写入 {total_written} 条记录",
            {"rows": total_written},
        )
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="从 The Graph 导入 Uniswap swap 数据")
    parser.add_argument("--task-id", dest="task_id", help="任务 ID", default=None)
    parser.add_argument("--config", dest="config", help="JSON 配置", default=None)
    args = parser.parse_args()
    run_collect_uniswap(args.task_id, args.config)


if __name__ == "__main__":
    main()
