package db

import (
	"log"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

var DB *gorm.DB

// InitDB 初始化数据库连接
func InitDB() {
	// dsn (Data Source Name) 是你的数据库连接字符串
	// 格式: "host=主机 user=用户名 password=密码 dbname=数据库名 port=端口 sslmode=disable TimeZone=Asia/Shanghai"
	dsn := "host=localhost user=postgres password=mysecretpassword dbname=etrade port=5432 sslmode=disable"
	var err error
	DB, err = gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	log.Println("Database connection established")
}
