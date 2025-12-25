# Etrade

<div align=center>
   <img src="https://img.shields.io/badge/gin-1.24-blue"/>
   <img src="https://img.shields.io/badge/vue-3.5-green"/>
   <img src="https://img.shields.io/badge/binance-uniswap-yellow"/>
</div>

## 简介

### 功能

Etrade 是一个用于 CEX-DEX 套利分析的一站式平台，主要针对 Uniswap V3 和 Binance 的 ETH/USDT 交易对进行分析。

系统采用微服务架构，核心数据流如下：

`[Vue.js 前端] -> [Go 后端 API (Gin)] -> [Python Worker (gRPC)] -> [PostgreSQL 数据库]`

架构说明：
- **Go 后端**：负责任务创建、调度与对外 API 服务
- **Python Worker**：执行数据采集、聚合、分析等具体任务，并写入任务日志与结果

![](images/architecture.png)

### 技术栈

使用技术栈为：
- PostgreSQL: 存储套利机会、交易记录、任务日志、批次/模板等数据
- Go (Gin): 请求处理、任务调度、Swagger 文档
- Python: 数据获取与分析（gRPC Worker + pandas/psycopg2）
- Vue: 前端看板（ant-design-vue / echarts）
- gRPC/Protobuf: 后端与 Worker 的任务派发接口

## 快速开始

### 前端

```bash
# 在 frontend 目录
npm install # 下载对应依赖
npm run dev # 运行项目
```

前端默认请求后端 `http://localhost:8888/api/v1`

**项目结构**（src 目录）：

- `api/`：API 接口层，使用 `axios` 与后端通信
- `assets/`：公共静态资源（CSS 等）
- `components/`：可复用组件
- `router/`：路由配置
- `views/`：页面组件
- `App.vue`、`main.ts`、`style.css`：应用入口和全局样式

> **提示**：如果 `tsconfig.app.json` 等配置文件中出现异常报错，经检查无实质性问题时，可能是缓存导致。可尝试删除并恢复相关语句/文件，通常即可解决。

### PostgreSQL

使用 Docker 部署 PostgreSQL，便于配置管理：

```bash
# 拉取镜像
docker pull postgres

# 运行容器（默认端口 5432，用户名 postgres，密码 123456）
docker run --name postgresql \
  -e POSTGRES_PASSWORD=123456 \
  -p 5432:5432 \
  -d postgres
```

> **注意**：确保 5432 端口可用，或根据需要修改映射端口。

**PgAdmin（可选）**

PgAdmin 用于可视化管理和查询 PostgreSQL，同样可通过 Docker 部署：

```bash
# 拉取 PgAdmin 镜像
docker pull dpage/pgadmin4

# 运行容器
docker run -d -p 5433:80 \
  --name pgadmin4 \
  -e PGADMIN_DEFAULT_EMAIL=test@123.com \
  -e PGADMIN_DEFAULT_PASSWORD=123456 \
  dpage/pgadmin4
```

> **重要**：在 PgAdmin 中连接 Docker 部署的 PostgreSQL 时，主机地址应使用 `host.docker.internal`，而非 `localhost` 或 `127.0.0.1`。

### RabbitMQ

使用 Docker 部署 RabbitMQ（含管理界面）：

```bash
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS=123456 \
  rabbitmq:management
```

管理界面地址：`http://localhost:15672`（用户名：admin，密码：123456）

### 后端

**启动步骤：**

```bash
cd backend
go mod tidy  # 安装依赖
go run main.go  # 启动服务（默认端口 8888）
```

**配置文件**

需要配置 `backend/config/config.yaml`：
- 数据库连接信息
- `worker.address`：Python Worker 地址

**API 文档**

Swagger 地址：`http://localhost:8888/swagger/index.html`

**项目结构（MVC 模式）**

- `api/`：HTTP 请求处理层
- `db/`：数据库连接配置
- `models/`：数据模型（数据库映射与请求/响应结构）
- `service/`：业务逻辑层（数据库操作与 Worker 任务派发）
- `utils/`：工具函数

**统一响应格式**

`utils/response.go` 定义了统一的 API 响应方法，响应格式如下：

```json
{
    "code": 200,
    "message": "",
    "data": []
}
```

使用示例：

```go
// 返回失败响应
utils.Fail(c, http.StatusInternalServerError, err.Error())
```

**数据模型规范**

建议为所有模型字段添加 GORM 标签，特别是非空约束。例如：

```go
type BinanceTrade struct {
	ID        uint      `gorm:"primaryKey"`
	TradeTime time.Time `gorm:"index;not null"`
	Price     float64   `gorm:"not null"`
	Quantity  float64   `gorm:"not null"`
}
```

### 数据分析引擎

Python Worker 负责执行数据采集、聚合和分析任务。

**启动步骤：**

```bash
cd data
pip install -r requirements.txt
python server.py
```

`data/server.py` 作为 gRPC Worker 服务，后端通过 `worker.address` 调用其执行各类任务。

## 系统部署指南

### 1. 依赖准备

- 操作系统：推荐 Linux 或 Windows（PowerShell）
- PostgreSQL：用于存储套利任务、批次、机会等数据（默认端口 5432）
- Go 1.20+：运行后端 API
- Python 3.10+：运行数据脚本/worker（建议使用虚拟环境 `.venv`）
- Node.js 18+：运行前端

环境变量建议：

```bash
# 在仓库根目录
python -m venv .venv
./.venv/Scripts/activate  # Windows 上运行
pip install -r data/requirements.txt

cd backend && go mod tidy
cd ../frontend && npm install
```

### 2. 数据库初始化

1. 在 PostgreSQL 中创建数据库 `etrade`（或在 `backend/config/config.yaml` 中自定义）。
2. 运行后端（见下）会自动执行 GORM 的 AutoMigrate，创建 `tasks/batches/arbitrage_opportunities` 等表。
3. 如需导入初始数据，可手动执行 SQL 或运行 `data/block_chain/collect_*` 脚本。

### 3. gRPC 代码生成（仅在修改 `protos/task.proto` 后需要）

仓库已包含生成后的 Python/Go 代码；如果你修改了 `protos/task.proto`，可按下面方式重新生成 Python 端代码：

```bash
pip install grpcio-tools
cd data
python -m grpc_tools.protoc -I .. --python_out=. --grpc_python_out=. ../protos/task.proto
```

生成文件会落在 `data/protos/` 下（对应 `from protos.task_pb2 import ...` 的导入路径）。

### 4. 数据脚本 Worker（Python）

Python 端负责实际执行任务（采集/分析）并写入日志：

```bash
cd data
# 启动 worker（默认读取 data/config/config.yaml，监听 worker_port=50052）
python server.py
```

`data/server.py` 会：
1. 监听 gRPC RPC（CollectBinance/CollectUniswap/ProcessPrices/Analyse）。
2. 读取 `data/config/config.yaml` 中的 DB 配置，写入 `task_logs` 并更新 `tasks.status`。
3. 调用 `data/block_chain/*.py` 执行具体任务。

### 5. Go 后端

后端同时暴露 HTTP (默认 `:8888`) 和内部 gRPC (默认 `:50060`)：

```bash
cd backend
go run main.go
```

- `backend/config/config.yaml` 的 `worker.address` 指定 Python Worker 地址（如 `127.0.0.1:50052`）。
- HTTP API 对外服务 `/api/v1/*`，Swagger 地址 `http://localhost:8888/swagger/index.html`。

### 6. 前端

```bash
cd frontend
npm install
npm run dev        # 开发模式
# 或 npm run build && npm run preview
```

### 7. 常见问题

- **任务一直 RUNNING**：确认 Python Worker 已启动，且后端 `worker.address` 指向正确端口；检查数据库 `task_logs` 是否有日志，若无则 Worker 未执行。
- **端口冲突**：Go HTTP `:8888`，Go gRPC `:50060`，Python Worker `:50052`。确保三者不冲突。
- **proto 导入失败**：确认 `data/protos/task_pb2.py` 与 `data/protos/task_pb2_grpc.py` 存在；建议从 `data/` 目录启动 Worker。

按以上步骤即可启动完整系统：先启动 PostgreSQL → Python Worker → Go 后端 → 前端；然后访问前端面板或 REST API，即可使用套利分析平台。

## 许可证

本项目采用 MIT License，详见仓库根目录 `LICENSE`。
