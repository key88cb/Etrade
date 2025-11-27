# Etrade

## 简介

### 功能

Etrade 是一个用于CEX-DEX套利分析的一站式平台，主要针对Uniswap V3和Binance 2025年9月的ETH/USDT交易对进行分析。核心处理流程如下：`[Python 脚本 (采集/分析)] -> [PostgreSQL 数据库] -> [Go 后端 API (Gin)] -> [Vue.js 前端 (浏览器)]`

![](images/architecture.png)

### 技术栈

使用技术栈为：
- PostgreSQL: 存储套利机会，交易记录
- go(gin): 请求处理
- python: 数据获取与分析
- vue: 看板，组件库 ant-design-vue 可视化库 echarts

## 快速开始

### 前端

```bash
# 在front目录
npm install # 下载对应依赖
npm run dev # 运行项目
```

前端项目结构，主要是src目录：

- api：接口，和后端对应，使用`axios`库
- assets：一些公用的css之类的资源
- components：可复用的组件
- router：动态路由组件
- views：vue页面
- app.vue/main.tx/style.css：一些全局配置

可能会在`tsconfig.app.json`这类配置文件里面出现一些很奇怪的报错，如果经检查确实没什么问题，很有可能是因为缓存机制，把报错的语句/文件删除了再恢复一般就正常了，实在有无法修复的奇怪报错可以忽略。

### postgresql

使用docker拉取，便于调整端口等配置。这里 postgresql 运行的端口用默认的 5432 端口（请确保这个端口可用，或者换到别的可用端口），默认用户名为postgres，密码就是123456，这个账号和密码用于访问数据库本身。

```bash
# 拉取 PostgreSQL
docker pull postgres
# 数据较多，最好创建一个数据卷
docker volume inspect postgre-data
# 运行，配置尽量不要改
docker run --name postgresql \
  -e POSTGRES_PASSWORD=123456 \
  -p 5432:5432 \
  -v postgre-data:/var/lib/postgresql/data \
  -d postgres
```

PgAdmin用于查询和管理PostgreSQL，同样可以使用docker拉取，下面的邮箱t`est@123.com`和密码是用于访问PgAdmin ，但注意PgAdmin中输入docker部署的本地服务器ip地址时需要使用`host.docker.internal`，而不是`localhost`或者`127.0.0.1`

```bash
# 一并拉取 pgadmin4 方便查询
docker pull dpage/pgadmin4

docker run -d -p 5433:80 
  --name pgadmin4 
  -e PGADMIN_DEFAULT_EMAIL=test@123.com 
  -e PGADMIN_DEFAULT_PASSWORD=123456 
  dpage/pgadmin4
```

### 后端

运行后端：

```bash
# 在backend目录
go mod tidy # 自动处理依赖关系
go run main.go # 运行项目，端口8888
```

项目结构，MVC模式：
- api：用于收发http请求
- db：数据库配置
- models：模型，用于数据库存储和出入参
- service：业务逻辑，可以与数据库交互
- utils：一些工具方法

需要注意`utils/response.go`中定义了统一的后端返回方法，只需要直接在api层调用这些方法返回就行了，统一的格式为：

```json
{
    "code": 200,
    "message": "",
    "data": []
}
```

比如要返回一个失败的请求，就可以

```go
utils.Fail(c, http.StatusInternalServerError, err.Error())
```

models中的结构体注释建议都写，因为这个项目中理论上正常的数据每一项都是非空的，比如

```go
type BinanceTrade struct {
	ID        uint      `gorm:"primaryKey"`
	TradeTime time.Time `gorm:"index;not null"`
	Price     float64   `gorm:"not null"`
	Quantity  float64   `gorm:"not null"`
}
```
