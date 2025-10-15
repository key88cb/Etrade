package models

import "time"

type UniswapSwap struct {
	ID         uint      `gorm:"primaryKey"`
	BlockTime  time.Time `gorm:"index"`
	Price      float64
	AmountETH  float64
	AmountUSDT float64
	GasPrice   int64
	TxHash     string `gorm:"unique"` // 交易哈希是唯一的
}
