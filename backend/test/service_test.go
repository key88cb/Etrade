package test

import (
	"backend/test/helper"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"gorm.io/gorm"

	"backend/db"
	"backend/service"
)

var test_db *gorm.DB
var test_db_config *db.DBConfig
var srv *service.Service

func TestMain(m *testing.M) {
	// 加载测试配置
	err := helper.LoadTestConfig()
	if err != nil {
		panic(err)
	}
	test_db_config = helper.GetTestDBConfig()
	if test_db_config == nil {
		panic("test_db_config is nil")
	}

	// 连接测试数据库
	test_db, err = helper.ConnectTestDB(test_db_config)
	if err != nil {
		panic(err)
	}

	// 创建服务
	srv = service.NewService(test_db)

	// 运行测试
	code := m.Run()

	// 关闭数据库
	sqlDB, err := test_db.DB()
	if err != nil {
		panic(err)
	}
	sqlDB.Close()

	// 退出
	os.Exit(code)
}

func TestDatabase(t *testing.T) {
	// 清空数据库
	err := helper.ClearTables(test_db_config, []string{"arbitrage_opportunities", "binance_trades", "uniswap_swaps", "aggregated_prices"})
	if err != nil {
		t.Fatalf("Failed to clear tables: %v", err)
	}
}

func TestAssertEqual(t *testing.T) {
	assert.Equal(t, 1, 1)
}
