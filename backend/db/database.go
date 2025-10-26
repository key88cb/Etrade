package db

import (
	"fmt"
	"log"
	"os"

	"backend/config"
	"backend/models"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

var db *gorm.DB

// InitDB 初始化数据库连接
func InitDB() error {
	config.LoadEnv()

	dsn := buildDSN()
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

func buildDSN() string {
	host := getEnv("DB_HOST", "localhost")
	port := getEnv("DB_PORT", "5432")
	user := getEnv("DB_USER", "postgres")
	password := getEnv("DB_PASSWORD", "")
	dbName := getEnv("DB_NAME", "etrade")
	sslMode := getEnv("DB_SSLMODE", "disable")
	timezone := getEnv("DB_TIMEZONE", "Asia/Shanghai")

	return fmt.Sprintf(
		"host=%s user=%s password=%s dbname=%s port=%s sslmode=%s TimeZone=%s",
		host,
		user,
		password,
		dbName,
		port,
		sslMode,
		timezone,
	)
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
