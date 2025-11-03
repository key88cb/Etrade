# 数据模块 (`data/`) 使用指南

## 目录结构与核心功能

- `config/config.yaml`: 存储所有配置信息，如数据库连接凭证、API密钥等。
- `requirements.txt`: 项目所需的 Python 依赖库。
- `collect_binance.py`: 从币安的历史交易数据CSV文件中导入数据到数据库。
- `collect_uniswap.py`: 通过 The Graph API 收集 Uniswap 的交易数据。
- `collect_uniswap_etherscan.py`: 通过 Etherscan API 收集 Uniswap 的交易数据（作为 The Graph 的替代方案）。
- `process_prices.py`: 对采集到的原始数据进行聚合处理，计算不同时间粒度的平均价格。
- `analyse.py`: 基于原始交易数据，分析中心化与去中心化交易所之间的套利机会。

## 环境配置

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **配置 `config.yaml`**:
    在运行任何脚本之前，请务必正确填写 `data/config/config.yaml` 文件中的所有字段，特别是数据库连接信息和 API 密钥。

## 推荐执行流程

1.  **数据采集**:
    - 运行 `collect_binance.py` 导入币安数据。
    - 运行 `collect_uniswap_etherscan.py` (推荐) 或 `collect_uniswap.py` 导入 Uniswap 数据。
    > **注意**: 两个 Uniswap 脚本都会向同一个 `uniswap_swaps` 表写入数据，请根据需要选择其一运行。`etherscan` 版本 API 速率稍快，但是网络可能不稳定。

2.  **数据聚合**:
    - （可选）运行 `process_prices.py` 将原始交易数据按分钟（或其他时间间隔）聚合，方便进行时间序列分析。

3.  **套利分析**:
    - 运行 `analyse.py` 来分析已采集的数据并找出潜在的套利机会。

---

## 脚本详细说明

### 数据采集脚本

#### `collect_binance.py`

- **功能**: 从一个大型CSV文件 (`ETHUSDT-trades-2025-09.csv`) 中读取币安的 ETH/USDT 交易对数据，并将其高效地存入 PostgreSQL 数据库。脚本采用分块读取和 `psycopg2` 的 `COPY` 命令，以实现高速导入。
- **输出数据表**: `binance_trades`
- **数据结构**:
  | 列名 | 数据类型 | 描述 |
  | :--- | :--- | :--- |
  | `id` | `bigint` | 交易ID |
  | `price` | `float8` | 成交价格 |
  | `qty` | `float8` | 成交数量 (ETH) |
  | `quote_qty` | `float8` | 成交额 (USDT) |
  | `trade_time` | `timestamptz` | 交易时间 (UTC) |
  | `is_buyer_maker` | `boolean` | 买方是否是做市方 |
  | `is_best_match` | `boolean` | 是否是最佳匹配 |

---

#### `collect_uniswap.py`

- **功能**: 通过 Uniswap 的 The Graph API 查询特定资金池（WETH/USDT）的 `Swap` 事件。该脚本通过分页查询获取指定时间范围内的所有交易。
- **输出数据表**: `uniswap_swaps`
- **数据结构**:
  | 列名 | 数据类型 | 描述 |
  | :--- | :--- | :--- |
  | `id` | `serial` (主键) | 自增ID |
  | `block_time` | `timestamptz` | 交易所在的区块时间 (UTC) |
  | `price` | `numeric` | 交易价格 (USDT/ETH) |
  | `amount_eth` | `numeric` | ETH 数量变动 |
  | `amount_usdt` | `numeric` | USDT 数量变动 |
  | `gas_price` | `numeric` | 交易的 Gas 价格 (Wei) |
  | `tx_hash` | `text` | 交易哈希 |

---

#### `collect_uniswap_etherscan.py`

- **功能**: 作为 `collect_uniswap.py` 的替代方案，此脚本通过 Etherscan API 获取指定资金池地址的代币转账记录。它首先根据时间戳找到对应的区块号，然后拉取该区块范围内的所有交易。此方法对于获取历史数据通常更可靠。
- **输出数据表**: `uniswap_swaps` (与 `collect_uniswap.py` 相同)
- **数据结构**: 与 `collect_uniswap.py` 完全相同。脚本内部包含一个 `setup_database_table` 函数，如果表不存在，会自动创建。

---

### 数据处理与分析脚本

#### `process_prices.py`

- **功能**: 读取 `binance_trades` 和 `uniswap_swaps` 表中的原始数据，按指定的时间间隔（例如 `minute`）进行分组，并计算每个时间窗口内两个来源的平均价格。
- **输入数据表**: `binance_trades`, `uniswap_swaps`
- **输出数据表**: `aggregated_prices` (每次运行时会先删除旧表再创建新表)
- **数据结构**:
  | 列名 | 数据类型 | 描述 |
  | :--- | :--- | :--- |
  | `time_bucket` | `timestamptz` | 聚合时间窗口的起始点 |
  | `source` | `text` | 数据来源 ('Binance' 或 'Uniswap') |
  | `average_price` | `numeric` | 在该时间窗口内的平均价格 |

---

#### `analyse.py`

- **功能**: 核心分析脚本。它从数据库加载币安和 Uniswap 的交易数据，并逐条比对两个市场在相近时间点的价格差异。脚本会考虑交易手续费、Gas成本和执行延迟，计算两种套利路径（币安买->Uniswap卖，Uniswap买->币安卖）的潜在利润。
- **输入数据表**: `binance_trades`, `uniswap_swaps`
- **输出数据表**: `arbitrage_opportunities` (每次运行时会先删除旧表再创建新表)
- **数据结构**:
  | 列名 | 数据类型 | 描述 |
  | :--- | :--- | :--- |
  | `buy_platform` | `text` | 建议的购买平台 ('Binance' 或 'Uniswap') |
  | `sell_platform` | `text` | 建议的出售平台 ('Binance' 或 'Uniswap') |
  | `buy_price` | `numeric` | 购买价格 |
  | `sell_price` | `numeric` | 出售价格 |
  | `profit_usdt` | `numeric` | 扣除所有费用后的净利润 (USDT) |
