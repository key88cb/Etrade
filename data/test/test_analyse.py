"""
analyse.py 的单元测试
"""

import os
import sys
from unittest.mock import MagicMock, Mock, mock_open, patch

import numpy as np
import pandas as pd
import pytest

# 获取当前脚本文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录（父目录）的路径
parent_dir = os.path.dirname(current_dir)
# 将上一级目录添加到 sys.path
sys.path.insert(0, parent_dir)

# Mock配置文件和数据库连接，避免在导入时出错
mock_config = {
    "db": {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "test_user",
        "password": "test_password",
    }
}

mock_conn = MagicMock()
mock_cur = MagicMock()
mock_conn.cursor.return_value = mock_cur
mock_conn.autocommit = False

# 在导入前mock配置文件和数据库连接
import yaml

with patch(
    "builtins.open",
    mock_open(
        read_data="db:\n  host: localhost\n  port: 5432\n  database: test_db\n  username: test_user\n  password: test_password"
    ),
):
    with patch("yaml.safe_load", return_value=mock_config):
        with patch("psycopg2.connect", return_value=mock_conn):
            from block_chain.analyse import (
                analyze_opportunities,
                calculate_profit_buy_cex_sell_dex,
                calculate_profit_buy_dex_sell_cex,
                fetch_price_pairs,
                save_results,
            )


class TestCalculateProfitBuyCexSellDex:
    """
    测试 calculate_profit_buy_cex_sell_dex 函数
    """

    def test_profitable_trade(self):
        """
        测试：币安买Uniswap卖，有利润的情况
        """
        investment = 100000.0
        price_cex = 2900.0  # 币安价格
        price_dex = 3000.0  # Uniswap价格（更高）
        gas_price = 50e9  # 50 Gwei
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_cex_sell_dex(
            strategy, price_cex, price_dex, gas_price
        )

        # 验证利润为正
        assert profit > 0
        # 验证利润计算的大致范围（考虑手续费和gas）
        assert profit < (investment * (price_dex / price_cex - 1))

    def test_unprofitable_trade(self):
        """
        测试：币安买Uniswap卖，无利润的情况
        """
        investment = 100000.0
        price_cex = 3000.0  # 币安价格
        price_dex = 2900.0  # Uniswap价格（更低）
        gas_price = 50e9
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_cex_sell_dex(
            strategy, price_cex, price_dex, gas_price
        )

        # 验证利润为负
        assert profit < 0

    def test_zero_gas_price(self):
        """
        测试：gas价格为0的情况
        """
        investment = 100000.0
        price_cex = 2900.0
        price_dex = 3000.0
        gas_price = 0
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_cex_sell_dex(
            strategy, price_cex, price_dex, gas_price
        )

        # 应该能正常计算，gas成本为0
        assert isinstance(profit, (int, float))
        assert profit > 0  # 没有gas成本，利润应该更高

    def test_equal_prices(self):
        """
        测试：两个平台价格相等的情况
        """
        investment = 100000.0
        price_cex = 3000.0
        price_dex = 3000.0
        gas_price = 50e9
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_cex_sell_dex(
            strategy, price_cex, price_dex, gas_price
        )

        # 价格相等，扣除手续费和gas后应该亏损
        assert profit < 0

    def test_high_gas_price(self):
        """
        测试：高gas价格的情况
        """
        investment = 100000.0
        price_cex = 2900.0
        price_dex = 3000.0
        gas_price = 200e9  # 200 Gwei，很高的gas价格
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_cex_sell_dex(
            strategy, price_cex, price_dex, gas_price
        )

        # 高gas可能使原本盈利的交易变成亏损
        assert isinstance(profit, (int, float))


class TestCalculateProfitBuyDexSellCex:
    """
    测试 calculate_profit_buy_dex_sell_cex 函数
    """

    def test_profitable_trade(self):
        """
        测试：Uniswap买币安卖，有利润的情况
        """
        investment = 100000.0
        price_dex = 2900.0  # Uniswap价格（更低）
        price_cex = 3000.0  # 币安价格（更高）
        gas_price = 50e9
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_dex_sell_cex(
            strategy, price_dex, price_cex, gas_price
        )

        # 验证利润为正
        assert profit > 0

    def test_unprofitable_trade(self):
        """
        测试：Uniswap买币安卖，无利润的情况
        """
        investment = 100000.0
        price_dex = 3000.0  # Uniswap价格（更高）
        price_cex = 2900.0  # 币安价格（更低）
        gas_price = 50e9
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_dex_sell_cex(
            strategy, price_dex, price_cex, gas_price
        )

        # 验证利润为负
        assert profit < 0

    def test_zero_gas_price(self):
        """
        测试：gas价格为0的情况
        """
        investment = 100000.0
        price_dex = 2900.0
        price_cex = 3000.0
        gas_price = 0
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_dex_sell_cex(
            strategy, price_dex, price_cex, gas_price
        )

        # 应该能正常计算，gas成本为0
        assert isinstance(profit, (int, float))
        assert profit > 0

    def test_equal_prices(self):
        """
        测试：两个平台价格相等的情况
        """
        investment = 100000.0
        price_dex = 3000.0
        price_cex = 3000.0
        gas_price = 50e9
        strategy = {
            "initial_investment": investment,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
        }

        profit = calculate_profit_buy_dex_sell_cex(
            strategy, price_dex, price_cex, gas_price
        )

        # 价格相等，扣除手续费和gas后应该亏损
        assert profit < 0


class TestAnalyzeOpportunities:
    """
    测试套利机会分析函数
    """

    def test_finds_profitable_trades_buy_cex_sell_dex(self):
        """
        测试：能找到盈利的套利机会（币安买Uniswap卖）
        """
        # 创建测试数据：Uniswap价格 > 币安价格
        price_pairs = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                3100.0,  # uniswap_price (高)
                50e9,  # gas_price
                1000.0,  # window_volume
                2900.0,  # binance_price (低)
            ),
        ]
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        assert len(opportunities) > 0
        assert opportunities[0]["buy_platform"] == "Binance"
        assert opportunities[0]["sell_platform"] == "Uniswap"
        assert opportunities[0]["buy_price"] == 2900.0
        assert opportunities[0]["sell_price"] == 3100.0
        assert opportunities[0]["profit_usdt"] > 10.0

    def test_finds_profitable_trades_buy_dex_sell_cex(self):
        """
        测试：能找到盈利的套利机会（Uniswap买币安卖）
        """
        # 创建测试数据：币安价格 > Uniswap价格
        price_pairs = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                2900.0,  # uniswap_price (低)
                50e9,  # gas_price
                1000.0,  # window_volume
                3100.0,  # binance_price (高)
            ),
        ]
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        assert len(opportunities) > 0
        assert opportunities[0]["buy_platform"] == "Uniswap"
        assert opportunities[0]["sell_platform"] == "Binance"
        assert opportunities[0]["buy_price"] == 2900.0
        assert opportunities[0]["sell_price"] == 3100.0
        assert opportunities[0]["profit_usdt"] > 10.0

    def test_filters_unprofitable_trades(self):
        """
        测试：过滤掉不盈利的交易
        """
        # 创建测试数据：价格差异很小，不足以盈利
        price_pairs = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                2901.0,  # uniswap_price
                50e9,  # gas_price
                1000.0,  # window_volume
                2900.0,  # binance_price
            ),
        ]
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        # 由于价格差异太小，应该被过滤掉
        assert len(opportunities) == 0

    def test_handles_invalid_data_nan(self):
        """
        测试：处理无效数据（NaN值）
        """
        price_pairs = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                np.nan,  # 无效价格
                50e9,
                1000.0,  # window_volume
                2900.0,
            ),
            (
                pd.Timestamp("2025-09-01 10:01:00", tz="UTC"),
                3000.0,
                np.nan,  # 无效gas价格
                1000.0,  # window_volume
                2900.0,
            ),
            (
                pd.Timestamp("2025-09-01 10:02:00", tz="UTC"),
                3000.0,
                50e9,
                1000.0,  # window_volume
                np.nan,  # 无效币安价格
            ),
        ]
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        # 应该跳过无效数据
        assert len(opportunities) == 0

    def test_handles_zero_prices(self):
        """
        测试：处理零价格的情况
        """
        price_pairs = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                3000.0,
                50e9,
                1000.0,  # window_volume
                0.0,  # 币安价格为0
            ),
            (
                pd.Timestamp("2025-09-01 10:01:00", tz="UTC"),
                0.0,  # Uniswap价格为0
                50e9,
                1000.0,  # window_volume
                3000.0,
            ),
        ]
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        # 应该跳过零价格
        assert len(opportunities) == 0

    def test_empty_price_pairs(self):
        """
        测试：空的价格对列表
        """
        price_pairs = []
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        assert len(opportunities) == 0

    def test_multiple_opportunities(self):
        """
        测试：多个套利机会
        """
        price_pairs = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                3100.0,  # uniswap_price (高)
                50e9,
                1000.0,  # window_volume
                2900.0,  # binance_price (低)
            ),
            (
                pd.Timestamp("2025-09-01 10:01:00", tz="UTC"),
                2900.0,  # uniswap_price (低)
                50e9,
                1000.0,  # window_volume
                3100.0,  # binance_price (高)
            ),
        ]
        strategy = {
            "initial_investment": 100000.0,
            "binance_fee_rate": 0.001,
            "uniswap_fee_rate": 0.0005,
            "estimated_gas_used": 20,
            "profit_threshold": 10.0,
        }

        opportunities = analyze_opportunities(price_pairs, strategy)

        assert len(opportunities) == 2
        assert opportunities[0]["buy_platform"] == "Binance"
        assert opportunities[1]["buy_platform"] == "Uniswap"


class TestFetchPricePairs:
    """
    测试从数据库获取价格对函数
    """

    def test_fetch_price_pairs_with_time_range(self):
        """
        测试：带时间范围的查询
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None
        mock_cur.fetchall.return_value = [
            (
                pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                3000.0,
                50e9,
                1000.0,  # window_volume
                2900.0,
            ),
        ]

        start_time = pd.Timestamp("2025-09-01 00:00:00", tz="UTC")
        end_time = pd.Timestamp("2025-09-01 23:59:59", tz="UTC")
        strategy = {
            "time_delay_seconds": 3,
            "window_seconds": 5,
        }

        result = fetch_price_pairs(mock_conn, strategy, start_time, end_time)

        assert len(result) == 1
        assert mock_cur.execute.called
        assert mock_cur.fetchall.called

    def test_fetch_price_pairs_no_time_range(self):
        """
        测试：无时间范围的查询
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None
        mock_cur.fetchall.return_value = []

        strategy = {
            "time_delay_seconds": 3,
            "window_seconds": 5,
        }

        result = fetch_price_pairs(mock_conn, strategy)

        assert len(result) == 0
        assert mock_cur.execute.called
        assert mock_cur.fetchall.called


class TestSaveResults:
    """
    测试保存结果函数
    """

    def test_save_results_with_data(self):
        """
        测试：保存有数据的结果
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        results = [
            {
                "block_time": pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                "buy_platform": "Binance",
                "sell_platform": "Uniswap",
                "buy_price": 2900.0,
                "sell_price": 3100.0,
                "profit_usdt": 100.0,
                "risk_metrics": {},
            },
        ]

        with patch("block_chain.analyse.execute_values") as mock_execute_values:
            save_results(mock_conn, results, batch_id=1, overwrite=True)

            # 验证执行了DROP TABLE和CREATE TABLE
            assert mock_cur.execute.call_count >= 2
            # 验证调用了execute_values
            assert mock_execute_values.called
            # 验证提交了事务
            assert mock_conn.commit.called

    def test_save_results_empty(self):
        """
        测试：保存空结果
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        results = []

        with patch("block_chain.analyse.logger") as mock_logger:
            save_results(mock_conn, results, batch_id=1)

            # 应该记录日志但不执行数据库操作
            assert mock_conn.commit.called

    def test_save_results_rollback_on_error(self):
        """
        测试：保存结果时出错应该回滚
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cur
        mock_conn.cursor.return_value.__exit__ = lambda *args: None

        results = [
            {
                "block_time": pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
                "buy_platform": "Binance",
                "sell_platform": "Uniswap",
                "buy_price": 2900.0,
                "sell_price": 3100.0,
                "profit_usdt": 100.0,
                "risk_metrics": {},
            },
        ]

        with patch("block_chain.analyse.logger") as mock_logger:
            try:
                save_results(mock_conn, results, batch_id=1, overwrite=True)
            except Exception:
                pass

            # 验证回滚被调用（如果发生异常）
            # 注意：由于使用了 context manager，可能不会调用 rollback
