package helper

import (
	"backend/db"
	"backend/models"
	"database/sql"
	"fmt"

	_ "github.com/lib/pq"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// 清空数据库中的表
func ClearTables(dbConfig *db.DBConfig, tables []string) error {
	db, err := sql.Open("postgres", fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable", dbConfig.Host, dbConfig.Username, dbConfig.Password, dbConfig.Database, dbConfig.Port))
	if err != nil {
		return fmt.Errorf("连接数据库失败：%v", err)
	}
	defer db.Close()
	for _, table := range tables {
		_, err = db.Exec("DELETE FROM " + table)
		if err != nil {
			return fmt.Errorf("清空表失败：%v", err)
		}
	}
	return nil
}

// 连接测试数据库
func ConnectTestDB(dbConfig *db.DBConfig) (*gorm.DB, error) {
	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable", dbConfig.Host, dbConfig.Username, dbConfig.Password, dbConfig.Database, dbConfig.Port)

	db, err := gorm.Open(postgres.Open(dsn))

	if err != nil {
		return nil, fmt.Errorf("连接数据库失败：%v", err)
	}

	// 自动迁移表结构
	err = db.AutoMigrate(&models.ArbitrageOpportunity{}, &models.BinanceTrade{}, &models.UniswapSwap{}, &models.AggregatedPrice{})
	if err != nil {
		return nil, fmt.Errorf("数据库迁移失败：%v", err)
	}

	return db, nil
}
