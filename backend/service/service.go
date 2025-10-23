package service

import (
	"backend/db"
	"backend/models"

	"gorm.io/gorm"
)

type Service struct {
	db *gorm.DB
}

func NewService() *Service {
	return &Service{db: db.GetDB()}
}

func (s *Service) GetOpportunities() ([]models.ArbitrageOpportunity, error) {
	var opportunities []models.ArbitrageOpportunity
	err := s.db.Find(&opportunities).Error
	return opportunities, err
}
func (s *Service) GetPriceComparisonData() (map[string][][2]interface{}, error) {
	var results []models.AggregatedPrice

	// 1. 从 service 层访问数据库
	if err := s.db.Order("time_bucket asc").Find(&results).Error; err != nil {
		// 向上传递错误
		return nil, err
	}

	// 2. 在 service 层完成数据格式化 (这是业务逻辑的一部分)
	dataMap := make(map[string][][2]interface{})
	dataMap["uniswap"] = make([][2]interface{}, 0)
	dataMap["binance"] = make([][2]interface{}, 0)

	for _, r := range results {
		timestamp := r.TimeBucket.UnixMilli()
		price := r.AveragePrice

		if r.Source == "Uniswap" {
			dataMap["uniswap"] = append(dataMap["uniswap"], [2]interface{}{timestamp, price})
		} else if r.Source == "Binance" {
			dataMap["binance"] = append(dataMap["binance"], [2]interface{}{timestamp, price})
		}
	}

	// 3. 返回格式化好的 map 和 nil 错误
	return dataMap, nil
}
