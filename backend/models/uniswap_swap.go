package models

import "time"

type UniswapSwap struct {
	ID         uint      `gorm:"primaryKey"`
	BlockTime  time.Time `gorm:"index;not null"`
	Price      float64   `gorm:"not null"`
	AmountETH  float64   `gorm:"not null"`
	AmountUSDT float64   `gorm:"not null"`
	GasPrice   int64     `gorm:"not null"`
	TxHash     string    `gorm:"unique;not null"`
}
