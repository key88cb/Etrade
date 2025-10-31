import calendar
import datetime
import time

import pandas as pd
import psycopg2
import yaml
from loguru import logger
from psycopg2.extras import execute_values
from tqdm import tqdm

with open("config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)
    HOST = config["db"]["host"]
    PORT = config["db"]["port"]
    DATABASE = config["db"]["database"]
    USERNAME = config["db"]["username"]
    PASSWORD = config["db"]["password"]
    # 使用 psycopg2 连接数据库
conn = psycopg2.connect(
    host=HOST,
    port=PORT,
    dbname=DATABASE,
    user=USERNAME,
    password=PASSWORD,
)
conn.autocommit = False
cur = conn.cursor()
AGGREGATION_INTERVAL = "minute"
YEAR = 2025
MONTH = 9

logger.info("开始执行数据库端聚合...")
start_time = time.time()

# --- 2. 准备一个使用 psycopg2 占位符的 SQL 查询模板 ---
# 使用 %s 作为占位符依次传入 interval, start_date, end_date
sql_template = """
(
    SELECT 
        date_trunc(%s, block_time) AS time_bucket,
        'Uniswap' AS source,
        AVG(price) AS average_price
    FROM 
        uniswap_swaps
    WHERE 
        block_time BETWEEN %s AND %s
    GROUP BY 
        time_bucket
)
UNION ALL
(
    SELECT 
        date_trunc(%s, trade_time) AS time_bucket,
        'Binance' AS source,
        AVG(price) AS average_price
    FROM 
        binance_trades
    WHERE 
        trade_time BETWEEN %s AND %s
    GROUP BY 
        time_bucket
);
"""

num_days = calendar.monthrange(YEAR, MONTH)[1]
all_days_dfs = []
logger.info(
    f"正在聚合 {YEAR}-{MONTH} (共 {num_days} 天) 的数据，按 '{AGGREGATION_INTERVAL}' 粒度..."
)

# 4. 使用 tqdm 包裹循环 (保持不变)
for day in tqdm(range(1, num_days + 1), desc="聚合每日数据"):

    day_start = datetime.datetime(
        YEAR, MONTH, day, 0, 0, 0, tzinfo=datetime.timezone.utc
    )
    day_end = datetime.datetime(
        YEAR, MONTH, day, 23, 59, 59, tzinfo=datetime.timezone.utc
    )

    try:
        params = (
            AGGREGATION_INTERVAL,
            day_start,
            day_end,
            AGGREGATION_INTERVAL,
            day_start,
            day_end,
        )
        cur.execute(sql_template, params)
        rows = cur.fetchall()
        if rows:
            day_df = pd.DataFrame(
                rows, columns=["time_bucket", "source", "average_price"]
            )
            all_days_dfs.append(day_df)

    except Exception as e:
        # 错误会在这里被捕获
        logger.info(f"\n处理第 {day} 天数据时出错: {e}")


logger.info("\n所有天的数据已聚合，正在合并...")
if not all_days_dfs:
    logger.info("未聚合到任何数据。")
else:
    df_final = pd.concat(all_days_dfs)
    end_time = time.time()
    logger.info(f"聚合与合并完成！总耗时: {end_time - start_time:.2f} 秒")
    logger.info(f"总共获取到 {len(df_final)} 条聚合记录。")
    logger.info(f"正在将 {len(df_final)} 条聚合记录存入 aggregated_prices 表...")
    try:
        # 替换写入逻辑为 psycopg2: 先删除再创建表
        logger.info("正在重建 aggregated_prices 表...")
        cur.execute("DROP TABLE IF EXISTS aggregated_prices;")
        cur.execute(
            """
            CREATE TABLE aggregated_prices (
                time_bucket timestamptz,
                source text,
                average_price numeric
            );
            """
        )

        # 批量插入数据
        records = df_final[["time_bucket", "source", "average_price"]].values.tolist()
        logger.info(f"准备插入 {len(records)} 条记录...")
        execute_values(
            cur,
            "INSERT INTO aggregated_prices (time_bucket, source, average_price) VALUES %s",
            records,
        )
        conn.commit()
        logger.info("聚合价格数据存储成功并已提交！")
    except Exception as e:
        conn.rollback()
        logger.info(f"写入 aggregated_prices 表失败，已回滚。错误: {e}")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
