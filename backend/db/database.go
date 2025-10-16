package db

import (
	"log"

	"backend/models"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

var db *gorm.DB

// InitDB 初始化数据库连接
func InitDB() error {
	// dsn (Data Source Name) 是你的数据库连接字符串
	// 格式: "host=主机 user=用户名 password=密码 dbname=数据库名 port=端口 sslmode=disable TimeZone=Asia/Shanghai"
	dsn := "host=localhost user=postgres password=123456 dbname=etrade port=5432 sslmode=disable"
	var err error
	db, err = gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return err
	}

	log.Println("Database connection established")

	// 自动迁移数据库表
	err = db.AutoMigrate(
		&models.ArbitrageOpportunity{},
		&models.BinanceTrade{},
		&models.UniswapSwap{},
	)
	if err != nil {
		return err
	}
	return nil
}

func GetDB() *gorm.DB {
	return db
}
