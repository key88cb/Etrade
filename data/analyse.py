import pandas as pd
import yaml
from loguru import logger
import psycopg2
from psycopg2.extras import execute_values

# 1. 定义常量
# 交易成本
BINANCE_FEE_RATE = 0.001  # 币安吃单费率
UNISWAP_FEE_RATE = 0.0005  # Uniswap池费率
ESTIMATED_GAS_USED = 20  # Gas消耗量估算值

# 策略参数
INITIAL_INVESTMENT_USDT = 10000.0  # 每次套利的初始投入资金
TIME_DELAY_SECONDS = 3  # 非原子套利的执行延迟估算 (6秒)
PROFIT_THRESHOLD_USDT = 10  # 只记录利润大于1 USDT的机会
# 2. 数据库连接 (psycopg2)
with open("config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)
    HOST = config["db"]["host"]
    PORT = config["db"]["port"]
    DATABASE = config["db"]["database"]
    USERNAME = config["db"]["username"]
    PASSWORD = config["db"]["password"]

conn = psycopg2.connect(
    host=HOST,
    port=PORT,
    dbname=DATABASE,
    user=USERNAME,
    password=PASSWORD,
)
conn.autocommit = False
cur = conn.cursor()


def load_data():
    logger.info("正在从数据库加载数据...")
    # 只提取分析所需列，减少内存开销
    cur.execute("SELECT block_time, price, gas_price FROM uniswap_swaps")
    uni_rows = cur.fetchall()
    uniswap_df = pd.DataFrame(uni_rows, columns=["block_time", "price", "gas_price"])
    # 将 Decimal/NUMERIC 转为 float，避免 float 与 Decimal 混算错误
    uniswap_df["price"] = pd.to_numeric(uniswap_df["price"], errors="coerce").astype(
        float
    )
    uniswap_df["gas_price"] = pd.to_numeric(
        uniswap_df["gas_price"], errors="coerce"
    ).astype(float)

    cur.execute("SELECT trade_time, price FROM binance_trades")
    bin_rows = cur.fetchall()
    binance_df = pd.DataFrame(bin_rows, columns=["trade_time", "price"])
    binance_df["price"] = pd.to_numeric(binance_df["price"], errors="coerce").astype(
        float
    )

    # 转换时间戳为datetime对象，并统一为UTC时区
    uniswap_df["block_time"] = pd.to_datetime(uniswap_df["block_time"], utc=True)
    binance_df["trade_time"] = pd.to_datetime(binance_df["trade_time"], utc=True)

    # 将时间戳设置为索引
    uniswap_df.set_index("block_time", inplace=True)
    binance_df.set_index("trade_time", inplace=True)

    # 在使用 .loc 时间切片之前，必须确保索引已排序
    logger.info("正在排序索引 (这对于大型DataFrame可能需要一些时间)...")
    uniswap_df.sort_index(inplace=True)
    binance_df.sort_index(inplace=True)
    logger.info("索引排序完成。")

    logger.info(
        f"加载完成: {len(uniswap_df)} 条Uniswap记录, {len(binance_df)} 条币安记录"
    )
    if not uniswap_df.empty:
        logger.info(
            f"Uniswap 数据时间范围: {uniswap_df.index.min()} -> {uniswap_df.index.max()}"
        )
    if not binance_df.empty:
        logger.info(
            f"Binance 数据时间范围: {binance_df.index.min()} -> {binance_df.index.max()}"
        )

    return uniswap_df, binance_df


def calculate_profit_buy_cex_sell_dex(investment, price_cex, price_dex, gas_price):
    eth_acquired = (investment * (1 - BINANCE_FEE_RATE)) / price_cex
    gross_revenue_usdt = eth_acquired * price_dex
    uniswap_fee = gross_revenue_usdt * UNISWAP_FEE_RATE

    gas_cost_eth = (ESTIMATED_GAS_USED * gas_price) / 1e18
    gas_cost_usdt = gas_cost_eth * price_dex

    final_usdt = gross_revenue_usdt - uniswap_fee
    net_profit = final_usdt - investment - gas_cost_usdt
    return net_profit


def calculate_profit_buy_dex_sell_cex(investment, price_dex, price_cex, gas_price):
    gas_cost_eth = (ESTIMATED_GAS_USED * gas_price) / 1e18
    gas_cost_usdt = gas_cost_eth * price_dex

    total_investment = investment + gas_cost_usdt
    uniswap_fee = investment * UNISWAP_FEE_RATE

    eth_acquired = (investment - uniswap_fee) / price_dex
    gross_revenue_usdt = eth_acquired * price_cex
    binance_fee = gross_revenue_usdt * BINANCE_FEE_RATE

    final_usdt = gross_revenue_usdt - binance_fee
    net_profit = final_usdt - total_investment
    return net_profit


def analyze_opportunities(uniswap_df, binance_df):
    logger.info("开始分析套利机会...")
    profitable_trades = []

    #
    for index, swap in uniswap_df.iterrows():
        uniswap_price = swap["price"]
        uniswap_time = index
        gas_price = swap["gas_price"]

        # 计算出需要在币安上查询价格的时间点
        binance_lookup_time = uniswap_time - pd.Timedelta(seconds=TIME_DELAY_SECONDS)

        # 在币安数据中查找这个时间点附近的价格
        # 取一个10秒的小窗口，计算平均价，平滑噪音
        window_start = binance_lookup_time - pd.Timedelta(seconds=5)
        window_end = binance_lookup_time + pd.Timedelta(seconds=5)

        relevant_binance_trades = binance_df.loc[window_start:window_end]

        if relevant_binance_trades.empty:
            continue  # 如果这个时间窗口内币安没有交易，则跳过

        binance_price = relevant_binance_trades["price"].mean()

        # 方向1: 币安买, Uniswap卖
        # 条件: Uniswap价格 > 币安价格
        if uniswap_price > binance_price:
            profit = calculate_profit_buy_cex_sell_dex(
                INITIAL_INVESTMENT_USDT, binance_price, uniswap_price, gas_price
            )
            if profit > PROFIT_THRESHOLD_USDT:
                logger.info(f"发现机会! 利润: ${profit:.2f} USDT")
                profitable_trades.append(
                    {
                        "buy_platform": "Binance",
                        "sell_platform": "Uniswap",
                        "buy_price": binance_price,
                        "sell_price": uniswap_price,
                        "profit_usdt": profit,
                        # 可以添加更多信息，如时间戳等
                    }
                )

        # 方向2: Uniswap买, 幣安卖
        # 条件: 币安价格 > Uniswap价格
        elif binance_price > uniswap_price:
            profit = calculate_profit_buy_dex_sell_cex(
                INITIAL_INVESTMENT_USDT, uniswap_price, binance_price, gas_price
            )
            if profit > PROFIT_THRESHOLD_USDT:
                logger.info(f"发现机会! 利润: ${profit:.2f} USDT")
                profitable_trades.append(
                    {
                        "buy_platform": "Uniswap",
                        "sell_platform": "Binance",
                        "buy_price": uniswap_price,
                        "sell_price": binance_price,
                        "profit_usdt": profit,
                    }
                )

    return profitable_trades


def save_results(results):
    if not results:
        logger.info("未发现任何符合条件的套利机会。")
        return

    logger.info(f"分析完成，共发现 {len(results)} 条套利机会。正在存入数据库...")
    results_df = pd.DataFrame(results)
    try:
        logger.info("正在重建 arbitrage_opportunities 表...")
        cur.execute("DROP TABLE IF EXISTS arbitrage_opportunities;")
        cur.execute(
            """
            CREATE TABLE arbitrage_opportunities (
                buy_platform text,
                sell_platform text,
                buy_price numeric,
                sell_price numeric,
                profit_usdt numeric
            );
            """
        )

        if not results_df.empty:
            records = results_df[
                [
                    "buy_platform",
                    "sell_platform",
                    "buy_price",
                    "sell_price",
                    "profit_usdt",
                ]
            ].values.tolist()
            execute_values(
                cur,
                "INSERT INTO arbitrage_opportunities (buy_platform, sell_platform, buy_price, sell_price, profit_usdt) VALUES %s",
                records,
            )
        conn.commit()
        logger.info("结果已成功存入 arbitrage_opportunities 表并提交！")
    except Exception as e:
        conn.rollback()
        logger.error(f"写入结果失败，已回滚。错误: {e}")


if __name__ == "__main__":
    # 1. 加载数据
    uniswap_df, binance_df = load_data()

    # 2. 执行分析
    opportunities = analyze_opportunities(uniswap_df, binance_df)

    # 3. 保存结果
    save_results(opportunities)

    # 4. 清理连接
    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
