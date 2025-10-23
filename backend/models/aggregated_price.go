package models

import "time"

type AggregatedPrice struct {
	TimeBucket   time.Time `gorm:"primaryKey"` // 按小时或分钟聚合的时间点
	Source       string    `gorm:"primaryKey"` // 'Binance' 或 'Uniswap'
	AveragePrice float64   `gorm:"not null"`
}
