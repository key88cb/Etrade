package models

// ArbitrageOpportunity 对应于 arbitrage_opportunities 表
type ArbitrageOpportunity struct {
	ID           uint    `gorm:"primaryKey" json:"id"`
	BuyPlatform  string  `json:"buy_platform"`
	SellPlatform string  `json:"sell_platform"`
	BuyPrice     float64 `json:"buy_price"`
	SellPrice    float64 `json:"sell_price"`
	ProfitUSDT   float64 `json:"profit_usdt"`
	// 添加更多字段，如时间戳等
}
