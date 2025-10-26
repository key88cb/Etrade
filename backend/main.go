// main.go
package main

import (
	"log"

	"backend/api"
	"backend/config"
	"backend/db"
)

func main() {
	// 1. 加载环境变量并初始化数据库连接
	config.LoadEnv()
	if err := db.InitDB(); err != nil {
		log.Fatalf("failed to initialize database: %v", err)
	}

	// 2. 设置并获取路由引擎
	r := api.SetupRouter()

	// 3. 启动HTTP服务
	r.Run(":8888")
}
