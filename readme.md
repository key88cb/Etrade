# Etrade

## 快速开始

### postgresql

开发环境可以使用docker拉取，这样比较快捷

```bash
# 拉取 PostgreSQL
docker pull postgres
# 一并拉取 pgadmin4 方便查询
docker pull dpage/pgadmin4
# 运行，配置尽量不要改
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=TsSzEpejXAjuCztYQRG3 \
  --name postgresql \
  postgres

docker run -d -p 5433:80 
  --name pgadmin4 
  -e PGADMIN_DEFAULT_EMAIL=test@123.com 
  -e PGADMIN_DEFAULT_PASSWORD=123456 
  dpage/pgadmin4
```

- 这里 postgre sql 运行的端口用默认的 5432 端口，然后默认用户名为postgres，密码就是输入的123456，这个账号和密码用于访问数据库本身。
- 而下面的邮箱test@123.com和密码是用于访问 pgadmin ，但注意 pgadmin 中输入服务器地址时需要输host.docker.internal，而不是localhost或者127.0.0.1

gorm使用有一些细节：

- postgre sql数组在go中对应什么类型，数组的类型可不是`[]int`（这个显然是切片），应该用`github.com/lib/pq`中的扩展类型<del>或者自己去实现</del>
- 字符串会默认存储为Text，Text（任意长字符串）其实一般也没问题，不过从设计角度可能`Varchar`要更好点，可以避免塞进去一些过于奇怪的东西，当然这是很极端的情况

### 环境配置

1. 复制根目录下的 `.env.example` 为 `.env`，并填入真实的数据库账号、密码等敏感信息（`.env` 已被加入 `.gitignore`，不会提交到仓库）。
2. 所有 Go/Python 服务都会在启动时自动读取 `.env`，也可以在 IDE 的运行配置中直接注入相同的环境变量。

### 后端

运行后端：

```bash
# 在backend目录
go mod tidy # 自动处理依赖关系
go run main.go # 运行项目，端口8888
```

项目结构，MVC模式：
- api：用于收发http请求，这是一个薄层，主要业务逻辑在service层
- db：数据库配置
- models：模型，用于数据库存储和出入参
- service：主要业务逻辑，这一层可以与数据库交互
- utils：一些工具方法

需要注意`utils/response.go`中定义了统一的后端返回方法，只需要直接在api层调用这些方法返回就行了，统一的格式为：

```json
{
    "code": 200,
    "message": "",
    "data": any
}
```

比如我要返回一个失败的请求，就可以

```go
utils.Fail(c, http.StatusInternalServerError, err.Error())
```

models中的结构体注释建议都写，因为这个项目中理论上正常的数据每一项都应该非空吧，比如

```go
type BinanceTrade struct {
	ID        uint      `gorm:"primaryKey"`
	TradeTime time.Time `gorm:"index;not null"`
	Price     float64   `gorm:"not null"`
	Quantity  float64   `gorm:"not null"`
}
```

Go 虽然没有 OOP，但很多时候写法都非常像OOP，比如会给一个构建函数（builder pattern），具体见api和service的写法

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

- 注意Vue组件和页面名都是大驼峰(Camel Case)
- 可能会在`tsconfig.app.json`这类配置文件里面出现一些很奇怪的报错，如果经检查确实没什么问题，很有可能是因为缓存机制，把报错的语句/文件删除了再恢复一般就正常了
- ts和js都是兼容的，有些库比如echats是js库，要在ts里面用需要引入相应的类型支持
- Vue使用组合式API

## 简介

### 技术栈

目前使用技术栈为：
- postgresql: 存储套利机会 交易记录
- go(gin): 请求处理
- python: 数据获取与分析
- vue: 看板，组件库 ant-design-vue 可视化库 echarts

### IDE 推荐

IDE与上手建议：
GO: goland 
PY: pycharm
前端: vscode
上手建议：没写过go的早点看看代码 写起来很快很简单


### git message 规范

提交格式：
- feat：新增功能（feature）
- fix：修复 bug
- docs：文档更新
- style：代码格式调整（不影响代码功能）
- refactor：重构代码
- test：添加或修改测试
- chore：构建过程或辅助工具的变更

例如：

> fix(payment-module): 修复支付超时 bug
