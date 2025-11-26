package helper

import (
	"backend/db"

	"github.com/spf13/viper"
)

var test_db_config *db.DBConfig

// 从配置文件加载配置
func LoadTestConfig() error {
	viper.SetConfigName("test.yaml")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("../config")
	err := viper.ReadInConfig()
	if err != nil {
		return err
	}
	test_db_config = &db.DBConfig{}
	test_db_config.Username = viper.GetString("db.username")
	test_db_config.Password = viper.GetString("db.password")
	test_db_config.Host = viper.GetString("db.host")
	test_db_config.Port = viper.GetString("db.port")
	test_db_config.Database = viper.GetString("db.database")
	return nil
}

func GetTestDBConfig() *db.DBConfig {
	return test_db_config
}
