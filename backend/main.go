package main

import (
	"backend/api"
	"backend/config"
	"backend/db"
	"log"

	docs "backend/docs" // 导入 swag 生成的 docs

	swaggerFiles "github.com/swaggo/files"     // 导入 swaggerFiles
	ginSwagger "github.com/swaggo/gin-swagger" // 导入 ginSwagger
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

	docs.SwaggerInfo.BasePath = "/api/v1" // 告诉 swag API 的基础路径
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	log.Println("Swagger UI is available at http://localhost:8888/swagger/index.html")

	// 3. 启动HTTP服务
	if err := r.Run(":8888"); err != nil {
		log.Printf("Failed to start HTTP server: %v", err)
	}
}
