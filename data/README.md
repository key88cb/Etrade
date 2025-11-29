# Etrade Data Processing Service (`data/`)

本目录包含 Etrade 系统的 Python 计算服务（Worker）。它负责执行高负载的数据处理任务，包括数据采集、清洗、聚合以及核心的量化分析策略。

## 1. 核心架构与工作流

Etrade 采用微服务架构，Python Worker 作为“执行单元”，接受 Go 后端的调度。

### 1.1 交互流程
1.  **调度 (Go -> Python)**:
    *   Go 后端通过 gRPC (`RunTask`) 向 Worker 发送指令。
    *   指令参数被序列化为 JSON，包含任务配置（如 `strategy`, `batch_id` 等）。
2.  **执行 (Python)**:
    *   Worker (`server.py`) 收到请求后，立即返回 `RUNNING` 状态（非阻塞）。
    *   Worker 启动后台线程运行具体脚本（如 `analyse.py`）。
3.  **反馈 (Python -> DB)**:
    *   **日志**: 脚本实时将进度写入 `task_logs` 表。
    *   **状态**: 任务完成后，脚本更新 `tasks` 表状态为 `SUCCESS`/`FAILED`。
    *   **数据**: 分析结果直接写入 `arbitrage_opportunities` 等业务表。

### 1.2 目录结构

*   **`server.py`**: **服务入口**。启动 gRPC Server，监听 50052 端口，负责任务分发和线程管理。
*   **`block_chain/`**: **核心业务逻辑**。
    *   `analyse.py`: 套利分析策略实现。
    *   `collect_binance.py`: CEX 数据导入工具。
    *   `collect_uniswap.py`: DEX 数据爬虫。
    *   `process_prices.py`: 价格聚合降采样工具。
*   **`config/`**: 配置文件（数据库连接、API Key）。
*   **`protos/`**: gRPC 协议生成的 Python 代码。

---

## 2. 通信协议与接口定义 (Protocol & API)

系统使用 gRPC 进行通信，接口定义见 `protos/task.proto`。

### 2.1 gRPC 请求 (`AnalyseRequest`)
当 Go 后端发起分析任务时，发送的消息结构如下：

| 字段名 | 类型 | 描述 | 示例值 |
| :--- | :--- | :--- | :--- |
| `task_id` | `string` | 任务唯一标识 (UUID) | `"a1b2-c3d4-..."` |
| `batch_id` | `int32` | 结果写入的批次 ID | `5` |
| `overwrite` | `bool` | 是否覆盖模式 (True=清空旧数据) | `true` |
| `strategy_json` | `string` | 策略参数的具体 JSON 字符串 | 见下文 |

#### `strategy_json` 结构详解
这是一个包含核心算法参数的 JSON 对象：
```json
{
  "time_delay_seconds": 3,       // 模拟链上延迟 (秒)
  "window_seconds": 5,           // 价格平均窗口 (秒)
  "profit_threshold": 10.0,      // 最小净利润阈值 (USDT)
  "initial_investment": 100000.0,// 模拟初始本金
  "binance_fee_rate": 0.001,     // 币安手续费 (0.1%)
  "uniswap_fee_rate": 0.0005,    // Uniswap 手续费 (0.05%)
  "estimated_gas_used": 20       // 估算单笔 Swap 消耗 Gas 量
}
```

### 2.2 gRPC 响应 (`TaskResponse`)
所有 RPC 方法（包括 `Analyse`）立即返回以下结构，**不等待任务执行完成**。

| 字段名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `task_id` | `string` | 确认收到的任务 ID |
| `status` | `enum` | 通常为 `TASK_STATUS_RUNNING` (0) |

> **关键点**: gRPC 响应只代表“任务已成功**入队**并开始后台运行”，**不包含**任何分析结果数据。

---

## 3. 核心机制详解

### 3.1 Python 分析函数 (`run_analyse`)
Worker 收到 gRPC 请求后，在后台线程调用此函数。

*   **输入参数**:
    *   `task_id` (str): 用于写日志和更新数据库状态。
    *   `config_json` (str): 将 gRPC 的 `batch_id`, `overwrite` 和 `strategy_json` 合并后的完整配置。
*   **返回对象**:
    *   **无显式返回值** (`None`)。
*   **结果输出机制 (副作用)**:
    *   函数并不将结果 `return` 给调用者。
    *   而是直接通过 `psycopg2` 连接，执行 `INSERT INTO arbitrage_opportunities ...`，将成百上千条分析结果写入 **PostgreSQL 数据库**。
    *   前端界面通过查询数据库的 `arbitrage_opportunities` 表（根据 `batch_id` 过滤）来展示最终结果。

### 3.2 Batch (批次) 管理
**Batch** 是连接“抽象算法”和“用户感知”的容器，用于隔离不同策略或时间段的分析结果。

*   **手动模式**: 用户在前端创建 Batch，Go 传参 `batch_id`，脚本将结果写入该 Batch。
*   **自动兜底**: 若未指定 Batch，脚本会自动检查并创建 "Auto Batch 1" 进行写入。
*   **覆盖逻辑**: 若请求参数 `overwrite=True`，脚本会先执行 `DELETE FROM ... WHERE batch_id = ...` 清空旧数据，确保结果纯净。

---

## 4. 配置与部署

### 4.1 远程数据库
修改 `config/config.yaml` 连接生产环境数据库：
```yaml
db:
  host: "121.196.205.18"
  port: 5432
  database: "etrade"
  username: "postgres"
  password: "..."
```

### 4.2 启动服务
```bash
# 确保依赖已安装
pip install -r requirements.txt

# 启动 gRPC Worker
python server.py
```

更多关于算法原理和数据表结构的细节，请参考 [data/block_chain/README.md](block_chain/README.md)。
