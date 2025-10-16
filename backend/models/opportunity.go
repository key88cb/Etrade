package models

// ArbitrageOpportunity 对应于 arbitrage_opportunities 表
type ArbitrageOpportunity struct {
	ID           uint    `json:"id" gorm:"primaryKey"`
	BuyPlatform  string  `json:"buy_platform" gorm:"not null;type:varchar(100)"`
	SellPlatform string  `json:"sell_platform" gorm:"not null;type:varchar(100)"`
	BuyPrice     float64 `json:"buy_price" gorm:"not null"`
	SellPrice    float64 `json:"sell_price" gorm:"not null"`
	ProfitUSDT   float64 `json:"profit_usdt" gorm:"not null"`
}
