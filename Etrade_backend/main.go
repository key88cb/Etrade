// main.go
package main

import (
	"Etrade_backend/api"
	"Etrade_backend/db"
	"Etrade_backend/models"
)

func main() {
	// 1. 初始化数据库连接
	db.InitDB()

	// 2. 自动迁移所有模型对应的数据库表
	// GORM会检查并创建这三张表
	err := db.DB.AutoMigrate(
		&models.ArbitrageOpportunity{},
		&models.BinanceTrade{},
		&models.UniswapSwap{},
	)
	if err != nil {
		// 处理迁移错误
	}

	// 3. 设置并获取路由引擎
	r := api.SetupRouter(db.DB)

	// 4. 启动HTTP服务
	r.Run(":8080")
}
