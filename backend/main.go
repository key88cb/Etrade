// main.go
package main

import (
	"backend/api"
	"backend/config"
	"backend/db"
	"log"
)

func main() {
	// 0. 读取配置文件
	err := config.ReadConfigFile()
	if err != nil {
		log.Printf("Failed to read config file: %v", err)
	}
	// 1. 初始化数据库连接
	if err := db.InitDB(); err != nil {
		log.Printf("Failed to initialize database: %v", err)
	}
	// 2. 设置并获取路由引擎
	r := api.SetupRouter()
	// 3. 启动HTTP服务
	if err := r.Run(":8888"); err != nil {
		log.Printf("Failed to start HTTP server: %v", err)
	}
}
