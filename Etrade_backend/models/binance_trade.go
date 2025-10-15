package models

import "time"

type BinanceTrade struct {
	ID        uint      `gorm:"primaryKey"`
	TradeTime time.Time `gorm:"index"` // 为时间戳创建索引以加快查询
	Price     float64
	Quantity  float64
}
