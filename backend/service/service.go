package service

import (
	"backend/models"
	"fmt"  // 导入 fmt
	"time" // 导入 time

	"gorm.io/gorm"
)

type Service struct {
	db *gorm.DB
}

func NewService(db *gorm.DB) *Service {
	return &Service{db: db}
}

// DB exposes the underlying connection for test setup.
func (s *Service) DB() *gorm.DB {
	return s.db
}

// 添加了分页和排序参数
func (s *Service) GetOpportunities(page, limit int, sortBy, order string, batchIDs []uint) ([]models.ArbitrageOpportunity, *models.PaginationData, error) {
	var opportunities []models.ArbitrageOpportunity
	var paginationData *models.PaginationData

	// 计算分页
	offset := (page - 1) * limit

	tx := s.db.Model(&models.ArbitrageOpportunity{})
	if len(batchIDs) > 0 {
		tx = tx.Where("batch_id IN ?", batchIDs)
	}

	// 计算总数
	var total int64
	if err := tx.Count(&total).Error; err != nil {
		return nil, nil, err
	}

	paginationData = &models.PaginationData{
		Total: total,
		Page:  page,
		Limit: limit,
	}

	// 构建排序
	orderBy := fmt.Sprintf("%s %s", sortBy, order)

	// 执行带分页和排序的查询
	err := tx.Order(orderBy).Offset(offset).Limit(limit).Find(&opportunities).Error

	return opportunities, paginationData, err
}

// 添加了 startTime 和 endTime 参数
func (s *Service) GetPriceComparisonData(startTime, endTime int64) (map[string][][2]interface{}, error) {
	var results []models.AggregatedPrice

	// 将毫秒时间戳转换为 time.Time
	start := time.UnixMilli(startTime).UTC()
	end := time.UnixMilli(endTime).UTC()

	// 1. 从 service 层访问数据库, 添加 WHERE 条件
	if err := s.db.
		Where("time_bucket BETWEEN ? AND ?", start, end).
		Order("time_bucket asc").
		Find(&results).Error; err != nil {
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
