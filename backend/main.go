// main.go
package main

import (
	"backend/api"
	"backend/db"
)

func main() {
	// 1. 初始化数据库连接
	db.InitDB()

	// 2. 设置并获取路由引擎
	r := api.SetupRouter()

	// 3. 启动HTTP服务
	r.Run(":8888")
}
