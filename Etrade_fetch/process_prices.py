import pandas as pd
from sqlalchemy import create_engine, text
import time
import datetime
import calendar
from tqdm import tqdm
import os

from dotenv import load_dotenv

load_dotenv()

# --- 配置 --- 记得改密码
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/etrade"
)
engine = create_engine(DB_CONNECTION_STRING)
AGGREGATION_INTERVAL = 'minute'
YEAR = 2025
MONTH = 9

print("开始执行数据库端聚合...")
start_time = time.time()

# --- 2. 准备一个使用“命名参数”的SQL查询模板 ---
# 我们使用 :interval, :start_date, :end_date 作为占位符
sql_template = text(f"""
(
    SELECT 
        date_trunc(:interval, block_time) AS time_bucket,
        'Uniswap' AS source,
        AVG(price) AS average_price
    FROM 
        uniswap_swaps
    WHERE 
        block_time BETWEEN :start_date AND :end_date
    GROUP BY 
        time_bucket
)
UNION ALL
(
    SELECT 
        date_trunc(:interval, trade_time) AS time_bucket,
        'Binance' AS source,
        AVG(price) AS average_price
    FROM 
        binance_trades
    WHERE 
        trade_time BETWEEN :start_date AND :end_date
    GROUP BY 
        time_bucket
);
""")

num_days = calendar.monthrange(YEAR, MONTH)[1]
all_days_dfs = []
print(f"正在聚合 {YEAR}-{MONTH} (共 {num_days} 天) 的数据，按 '{AGGREGATION_INTERVAL}' 粒度...")

# 4. 使用 tqdm 包裹循环 (保持不变)
for day in tqdm(range(1, num_days + 1), desc="聚合每日数据"):

    day_start = datetime.datetime(YEAR, MONTH, day, 0, 0, 0, tzinfo=datetime.timezone.utc)
    day_end = datetime.datetime(YEAR, MONTH, day, 23, 59, 59, tzinfo=datetime.timezone.utc)

    try:
        # --- 3. 将参数作为“字典”传递 ---
        day_df = pd.read_sql_query(
            sql_template,
            engine,
            params={
                "interval": AGGREGATION_INTERVAL,
                "start_date": day_start,
                "end_date": day_end
            }
        )

        if not day_df.empty:
            all_days_dfs.append(day_df)

    except Exception as e:
        # 错误会在这里被捕获
        print(f"\n处理第 {day} 天数据时出错: {e}")


print("\n所有天的数据已聚合，正在合并...")
if not all_days_dfs:
    print("未聚合到任何数据。")
else:
    df_final = pd.concat(all_days_dfs)
    end_time = time.time()
    print(f"聚合与合并完成！总耗时: {end_time - start_time:.2f} 秒")
    print(f"总共获取到 {len(df_final)} 条聚合记录。")
    print(f"正在将 {len(df_final)} 条聚合记录存入 aggregated_prices 表...")
    df_final.to_sql('aggregated_prices', engine, if_exists='replace', index=False)
    print("聚合价格数据存储成功！")
