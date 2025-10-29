package config

import (
	"github.com/spf13/viper"
)

func ReadConfigFile() error {
	viper.SetConfigName("config.yaml") // 在这里修改读取的配置文件
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./config")
	//viper.AutomaticEnv() // 自动读取环境变量
	err := viper.ReadInConfig()
	if err != nil {
		return err
	}
	return nil
}
