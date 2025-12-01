"""
Risk analysis logic module.
提供纯函数用于风险指标计算，被 analyse.py 调用。
"""

import math
from typing import Any, Dict


def calculate_risk_metrics_local(
    opportunity: Dict[str, Any],
    volatility: float,
    market_volume: float,
    investment_usdt: float,
) -> Dict[str, Any]:
    """
    计算单条机会的风险指标
    :param opportunity: 包含 buy_price, profit_usdt 等
    :param volatility: 当前时间窗口的价格波动率
    :param market_volume: 市场总成交量 (ETH)
    :param investment_usdt: 投入本金 (USDT)
    :return: 包含 risk_score, slippage 等的字典
    """
    # 1. 计算交易规模 (ETH)
    price = float(opportunity["buy_price"])
    trade_size_eth = investment_usdt / price if price > 0 else 0

    # 2. 滑点估算 (Square Root Law)
    # Impact = c * sigma * sqrt(Q / V)
    impact_constant = 2.0  # 冲击系数

    if market_volume <= 0:
        slippage_pct = 1.0
    else:
        slippage_pct = (
            impact_constant * volatility * math.sqrt(trade_size_eth / market_volume)
        )

    slippage_pct = min(slippage_pct, 1.0)

    # 3. 预估滑点成本
    estimated_slippage_cost = investment_usdt * slippage_pct

    # 4. 风险评分 (0-100)
    profit = float(opportunity["profit_usdt"])

    if profit <= 0:
        risk_score = 0
    else:
        # 剩余净利润 = 理论利润 - 滑点成本
        net_result = profit - estimated_slippage_cost
        # Score = (剩余利润 / 理论利润) * 100
        # 如果滑点吃掉了所有利润，分为0
        risk_score = max(0, min(100, (net_result / profit) * 100))

    return {
        "volatility": round(volatility, 6),
        "market_volume_eth": round(market_volume, 2),
        "trade_size_eth": round(trade_size_eth, 4),
        "estimated_slippage_pct": round(slippage_pct * 100, 4),
        "estimated_slippage_cost": round(estimated_slippage_cost, 2),
        "risk_score": round(risk_score, 1),
    }
