"""
测试配置文件和共享fixtures
"""

from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest


@pytest.fixture
def mock_db_connection():
    """
    模拟数据库连接和游标
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # 支持 context manager 模式: with conn.cursor() as cursor:
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    # psycopg2 cursor has a connection attribute that points back to the connection
    mock_cursor.connection = mock_conn
    # psycopg2 connection has an encoding attribute
    mock_conn.encoding = "UTF8"
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    return mock_conn, mock_cursor


@pytest.fixture
def sample_price_pairs():
    """
    示例价格对数据，用于测试分析函数
    """
    return [
        (
            pd.Timestamp("2025-09-01 10:00:00", tz="UTC"),
            3000.0,  # uniswap_price
            50e9,  # gas_price (50 Gwei)
            2900.0,  # binance_price
        ),
        (
            pd.Timestamp("2025-09-01 10:01:00", tz="UTC"),
            3100.0,  # uniswap_price
            50e9,  # gas_price
            3000.0,  # binance_price
        ),
        (
            pd.Timestamp("2025-09-01 10:02:00", tz="UTC"),
            2900.0,  # uniswap_price
            50e9,  # gas_price
            3000.0,  # binance_price
        ),
    ]


@pytest.fixture
def sample_uniswap_swaps():
    """
    示例Uniswap swap数据
    """
    return [
        {
            "id": "0x1",
            "timestamp": "1725187200",  # 2025-09-01 00:00:00 UTC
            "amount0": "1.0",
            "amount1": "3000.0",
            "transaction": {"id": "0xtx1", "gasPrice": "50000000000"},
        },
        {
            "id": "0x2",
            "timestamp": "1725187260",  # 2025-09-01 00:01:00 UTC
            "amount0": "2.0",
            "amount1": "6000.0",
            "transaction": {"id": "0xtx2", "gasPrice": "50000000000"},
        },
    ]


@pytest.fixture
def sample_binance_chunk():
    """
    示例币安CSV数据块
    """
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "price": [3000.0, 3001.0, 3002.0],
            "qty": [1.0, 2.0, 3.0],
            "quoteQty": [3000.0, 6002.0, 9006.0],
            "time": [
                1725187200000000,
                1725187260000000,
                1725187320000000,
            ],  # 微秒时间戳
            "isBuyerMaker": [True, False, True],
            "isBestMatch": [True, True, True],
        }
    )
