# Etrade 数据与算法核心模块 (`data/block_chain`)

本文档由项目开发过程中的技术讨论整理而成，旨在为开发者提供一份关于 Etrade 数据处理与套利算法的详尽技术指南。本模块是系统的核心执行单元，负责数据的采集、清洗、聚合以及核心的量化分析策略。

---

## 1. 系统架构与数据流

Etrade 采用 **Go (管控) + Python (计算) + PostgreSQL (存储)** 的混合架构。本目录 (`data/`) 包含的是 Python Worker 部分。

### 1.1 交互流程
1.  **任务发起**: 用户在 Vue 前端发起任务（如“采集币安数据”）。
2.  **调度**: Go 后端 (`backend/`) 接收请求，在数据库创建任务记录，并通过 gRPC (`RunTask`) 调用 Python Worker。
3.  **执行**: Python Worker (`server.py`) 收到请求：
    *   立即返回 `RUNNING` 状态，不阻塞 RPC 调用。
    *   启动后台线程执行具体的脚本（位于 `data/block_chain/`）。
    *   执行过程中，实时将日志写入 `task_logs` 表。
4.  **存储**: 脚本处理大量数据，直接利用 PostgreSQL 的 COPY 或 SQL 聚合能力进行读写。

### 1.2 远程数据库配置
Worker 依赖 `data/config/config.yaml` 连接数据库。若需连接远程生产库，请修改：
```yaml
db:
  host: "121.196.205.18"  # 远程 IP
  port: 5432
  database: "etrade"
  username: "postgres"
  password: "..."         # 对应密码
```

---

## 2. 数据库表结构详解 (Schema)

理解底层数据结构是理解上层算法的基础。以下是核心表的确切定义。

### A. 原始行情层 (Raw Data)

这部分数据量最大，是分析的源头。

#### 1. `binance_trades` (中心化交易所 - CEX)
*   **来源**: `collect_binance.py` (从 CSV 文件批量导入)。
*   **存储技术**: 使用 PostgreSQL `COPY FROM STDIN` 协议，导入速度比普通 INSERT 快数十倍。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `BIGINT` | 交易ID (主键) |
| `trade_time` | `TIMESTAMPTZ` | **交易发生时间**，核心时间锚点，精确到微秒/毫秒 |
| `price` | `NUMERIC` | 成交价格 (USDT) |
| `qty` | `NUMERIC` | 成交数量 (ETH) |
| `quote_qty` | `NUMERIC` | 成交总额 (USDT) |
| `is_buyer_maker` | `BOOLEAN` | 买方是否是挂单者 (`True`=主动卖单, `False`=主动买单) |
| `is_best_match` | `BOOLEAN` | 是否为最优撮合 |

#### 2. `uniswap_swaps` (去中心化交易所 - DEX)
*   **来源**: `collect_uniswap.py` (通过 The Graph GraphQL API 爬取)。
*   **时间精度**: **秒级**。因为数据源于以太坊区块时间 (`Block Timestamp`)。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `BIGINT` | 自增主键 |
| `block_time` | `TIMESTAMPTZ` | **区块时间**，UTC秒级时间戳 |
| `price` | `NUMERIC` | **成交价** (计算字段: `abs(amount1 / amount0)`) |
| `amount_eth` | `NUMERIC` | ETH 兑换数量 |
| `amount_usdt` | `NUMERIC` | USDT 兑换数量 |
| `gas_price` | `BIGINT` | **Gas 价格** (Wei)，用于计算链上成本 |
| `tx_hash` | `TEXT` | 交易哈希 |

### B. 分析结果层 (Analytical Results)

#### 3. `arbitrage_opportunities` (套利机会)
*   **来源**: `analyse.py` (核心算法生成)。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `id` | `BIGINT` | 自增主键 |
| `batch_id` | `BIGINT` | 批次 ID，用于将一次分析任务产生的所有机会归类 |
| `buy_platform` | `VARCHAR(100)` | 买入平台 (例如 "Binance") |
| `sell_platform` | `VARCHAR(100)` | 卖出平台 (例如 "Uniswap") |
| `buy_price` | `NUMERIC` | 买入价格 |
| `sell_price` | `NUMERIC` | 卖出价格 |
| `profit_usdt` | `NUMERIC` | **净利润** (已扣除双边手续费 + 链上 Gas 费) |
| `details_json` | `JSONB` | 元数据（如 `experiment_id`，具体的 `block_time` 等） |

#### 4. `aggregated_prices` (聚合行情)
*   **来源**: `process_prices.py`。
*   **用途**: 前端 ECharts 图表展示（分钟线/小时线）。

| 字段名 | 数据类型 | 描述 |
| :--- | :--- | :--- |
| `time_bucket` | `TIMESTAMPTZ` | 时间桶 (如每分钟的起始时间) |
| `source` | `TEXT` | 来源 ('Uniswap' 或 'Binance') |
| `average_price` | `NUMERIC` | 该时间段内的算术平均价 |

---

## 3. 模块功能详解

### 3.1 数据导入: `collect_binance.py` (ETL 搬运工)

负责将巨大的历史交易 CSV 文件高效导入数据库。

*   **核心逻辑**:
    1.  **估算行数**: 预读取文件估算总行数，用于计算进度条和支持“百分比导入”功能。
    2.  **分块读取**: 使用 `pandas.read_csv(chunksize=...)` 每次读取 100万行，避免 Python 内存溢出。
    3.  **数据清洗**: 重命名列 (`time` -> `trade_time`)，转换时间戳格式，去除无效行。
    4.  **极速写入**: 使用 `io.StringIO` 在内存中构建 CSV Buffer，然后调用 `psycopg2` 的 `cursor.copy_expert` 执行 `COPY binance_trades FROM STDIN`。
    *   **性能**: 这种方式比标准的 SQL `INSERT` 语句快几十倍，适合千万级数据导入。

### 3.2 数据爬虫: `collect_uniswap.py` (链上同步)

负责从 The Graph (GraphQL API) 抓取 Uniswap V3 的历史 Swap 记录。

*   **核心逻辑**:
    1.  **GraphQL 查询**: 构造查询语句，指定 `pool_address` 和时间范围。
    2.  **分页机制**: 由于 API 限制单次返回条数（通常 1000 条），代码维护一个 `last_id` 游标。每次查询都带上 `id_gt: last_id`，实现深度分页和断点续传。
    3.  **字段计算**: The Graph 返回的是原始的 `amount0` (ETH) 和 `amount1` (USDT)。脚本在内存中计算：
        $$ \text{Price} = \left| \frac{\text{amount1}}{\text{amount0}} \right| $$
    4.  **写入**: 清洗后的数据批量插入 `uniswap_swaps` 表。

### 3.3 数据聚合: `process_prices.py` (图表准备)

负责将海量的秒级/微秒级交易数据，降采样为分钟线或小时线，供前端绘制价格对比图。

*   **核心逻辑**:
    1.  **SQL 聚合**: 不在 Python 中处理数据，而是发送一条复杂的聚合 SQL 给数据库：
        ```sql
        -- 伪代码
        SELECT date_trunc('minute', block_time), 'Uniswap', AVG(price) ...
        UNION ALL
        SELECT date_trunc('minute', trade_time), 'Binance', AVG(price) ...
        ```
    2.  **全量覆盖**: 默认行为是 `overwrite=True`，即清空旧的聚合表并完全重写，确保数据的一致性。

---

## 4. 核心套利算法 (`analyse.py`) 深度解析

这是本项目的逻辑核心。它不依赖聚合表，而是直接在两张原始大表之间进行 **时空对齐** 和 **利润核算**。

### 4.1 算法目标
寻找满足以下条件的时刻：
$$ \text{价差收益} > (\text{双边手续费} + \text{链上 Gas 费}) $$

### 4.2 关键机制：时间对齐 (Time Alignment)

由于 Uniswap 是离散的（几秒一个区块），而 Binance 是高频连续的，我们无法直接匹配时间戳。算法采用 **“事件驱动 + 滑动窗口”** 机制。

*   **驱动源**: `uniswap_swaps`。以链上发生的每一笔 Swap 事件时间 $T_{uni}$ 为基准。
*   **匹配逻辑**: 对于每一个 $T_{uni}$，在 Binance 数据流中截取一个时间窗口。
*   **窗口公式**:
    $$ [T_{uni} - \text{delay} - \text{window}, \quad T_{uni} - \text{delay} + \text{window}] $$
    *   **Delay (延迟)**: 默认 3秒。模拟**DEX 数据上链延迟**以及数据传输、索引和机器人反应所需的物理时间。链上交易从提交到被打包进区块（上链）需要时间，且我们从节点或索引服务读到该数据又有延迟。如果我们不加延迟直接使用 $T_{uni}$ 时刻的中心化交易所价格，就相当于假设我们在链上交易发生的瞬间就“穿越时空”完成了对冲，这属于“利用未来信息作弊”（Look-ahead Bias）。
    *   **Window (窗口)**: 默认 5秒。在该区间内取 Binance 价格的 **算术平均值 (AVG)**，以平滑高频噪音。
*   **实现技术**: 算法**没有**把数据拉到 Python 内存处理，而是构造了一个复杂的 SQL 查询，利用 PostgreSQL 的 `CROSS JOIN` 和索引能力完成匹配：
    ```sql
    -- 伪代码逻辑
    SELECT ...
    FROM uniswap_swaps u
    JOIN binance_trades b 
      ON b.trade_time BETWEEN (u.block_time - delay - window) AND (u.block_time - delay + window)
    ```

### 4.3 利润计算模型 (Profit Model)

Python 脚本遍历 SQL 返回的对齐数据 $(P_{dex}, P_{cex}, P_{gas})$，套用以下数学公式。

**参数定义**:
*   $I$: 初始本金 (100,000 USDT)
*   $F_{cex}$: 币安手续费 (0.1% / 0.001)
*   $F_{dex}$: Uniswap 手续费 (0.05% / 0.0005)
*   $Cost_{gas}$: 链上交互成本 (USDT)
    $$ Cost_{gas} = \frac{\text{GasUsed} \times \text{GasPrice}}{10^{18}} \times P_{dex} $$

#### 场景 A: 正向套利 (Buy Binance -> Sell Uniswap)
策略：在 CEX 低价买入 ETH，搬运到 DEX 高价卖出。
1.  **CEX 买入 ETH**: $Q_{eth} = \frac{I \times (1 - F_{cex})}{P_{cex}}$
2.  **DEX 卖出获利**: $R_{gross} = Q_{eth} \times P_{dex}$
3.  **净利润**: 
    $$ \Pi = [R_{gross} \times (1 - F_{dex})] - I - Cost_{gas} $$

#### 场景 B: 反向套利 (Buy Uniswap -> Sell Binance)
策略：在 DEX 低价买入 ETH，搬运到 CEX 高价卖出。
1.  **DEX 买入 ETH**: $Q_{eth} = \frac{I \times (1 - F_{dex})}{P_{dex}}$
2.  **CEX 卖出获利**: $R_{gross} = Q_{eth} \times P_{cex}$
3.  **净利润**: 
    $$ \Pi = [R_{gross} \times (1 - F_{cex})] - (I + Cost_{gas}) $$
    *(注：此处我们将 Gas 费视为必须预先支付的沉没成本，计入总投入)*

只有当计算出的 $\Pi > \text{Threshold}$ (默认 10 USDT) 时，该机会才会被写入数据库。

---

## 5. 常见问题 (FAQ)

**Q1: 为什么 Uniswap 的时间精度是秒级？**
A: Uniswap V3 的交易是打包在以太坊区块中的。数据源（The Graph）返回的 `timestamp` 是该交易所在区块的出块时间（Block Timestamp）。目前以太坊出块稳定在 12秒左右，但时间戳通常精确到秒。

**Q2: 为什么要设置 Delay (延迟)？**
A: 为了模拟真实世界的物理延迟，特别是**DEX 数据的上链延迟**。在回测中，如果你在 $T$ 时刻看到链上价格，实际上该交易发生和确认的过程是有延迟的。此外，通常还需要几秒钟的数据传输和 API 交互时间才能在中心化交易所成交。设置 Delay 是为了防止回测结果虚高（Look-ahead Bias）。

**Q3: 这个算法是实时的还是回测的？**
A: 目前的设计主要用于 **离线分析/回测**。它依赖于数据库中已有的历史数据（`binance_trades` 和 `uniswap_swaps`）进行分析。但架构上，只要源源不断地写入新数据，该算法也可以通过调整时间窗口参数用于近实时分析。
