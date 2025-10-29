package db

import (
	"fmt"
	"log"

	"backend/models"

	"github.com/spf13/viper"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

var db *gorm.DB

type DBConfig struct {
	Host     string
	Port     string
	Username string
	Password string
	Database string
}

// InitDB 初始化数据库连接
func InitDB() error {
	// dsn (Data Source Name) 是你的数据库连接字符串
	// 格式: "host=主机 user=用户名 password=密码 dbname=数据库名 port=端口 sslmode=disable TimeZone=Asia/Shanghai"
	var config DBConfig
	config.Host = viper.GetString("db.host")
	config.Port = viper.GetString("db.port")
	config.Username = viper.GetString("db.username")
	config.Password = viper.GetString("db.password")
	config.Database = viper.GetString("db.database")
	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable", config.Host, config.Username, config.Password, config.Database, config.Port)
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return err
	}

	log.Println("Database connection established")

	// 自动迁移数据库表
	err = db.AutoMigrate(
		&models.ArbitrageOpportunity{},
		&models.BinanceTrade{},
		&models.UniswapSwap{},
		&models.AggregatedPrice{},
	)
	if err != nil {
		return err
	}
	return nil
}

func GetDB() *gorm.DB {
	return db
}
