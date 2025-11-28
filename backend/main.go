package main

import (
	"backend/api"
	"backend/config"
	"backend/db"
	"backend/grpcserver"
	"backend/service"
	"log"

	docs "backend/docs" // 导入 swag 生成的 docs

	"github.com/spf13/viper"
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
	taskManager := service.NewTaskManager(db.GetDB())
	templateService := service.NewTemplateService(db.GetDB())
	batchService := service.NewBatchService(db.GetDB())
	reportService := service.NewReportService(db.GetDB())

	go func() {
		grpcCfg := grpcserver.Config{
			Port:    viper.GetString("grpc.port"),
			Trigger: "grpc",
		}
		if err := grpcserver.Run(grpcCfg, taskManager); err != nil {
			log.Printf("Failed to start gRPC server: %v", err)
		}
	}()

	// 2. 设置并获取路由引擎
	taskHandler := api.NewTaskHandler(taskManager)
	templateHandler := api.NewTemplateHandler(templateService)
	batchHandler := api.NewBatchHandler(batchService)
	reportHandler := api.NewReportHandler(reportService)
	r := api.SetupRouter(taskHandler, templateHandler, batchHandler, reportHandler)

	docs.SwaggerInfo.BasePath = "/api/v1" // 告诉 swag API 的基础路径
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	log.Println("Swagger UI is available at http://localhost:8888/swagger/index.html")

	// 3. 启动HTTP服务
	if err := r.Run(":8888"); err != nil {
		log.Printf("Failed to start HTTP server: %v", err)
	}
}
