package models

import (
	"time"

	"gorm.io/datatypes"
)

// ArbitrageOpportunity 对应于 arbitrage_opportunities 表
type ArbitrageOpportunity struct {
	ID              uint              `json:"id" gorm:"primaryKey"`
	BatchID         uint              `json:"batch_id" gorm:"index"`
	BuyPlatform     string            `json:"buy_platform" gorm:"not null;type:varchar(100)"`
	SellPlatform    string            `json:"sell_platform" gorm:"not null;type:varchar(100)"`
	BuyPrice        float64           `json:"buy_price" gorm:"not null"`
	SellPrice       float64           `json:"sell_price" gorm:"not null"`
	ProfitUSDT      float64           `json:"profit_usdt" gorm:"not null"`
	DetailsJSON     datatypes.JSONMap `json:"details,omitempty" gorm:"type:jsonb" swaggertype:"object"`
	RiskMetricsJSON datatypes.JSONMap `json:"risk_metrics,omitempty" gorm:"type:jsonb" swaggertype:"object"`
	LLMAnalysisJSON datatypes.JSONMap `json:"llm_analysis,omitempty" gorm:"type:jsonb" swaggertype:"object"`
	CreatedAt       time.Time         `json:"created_at" gorm:"autoCreateTime"`
	UpdatedAt       time.Time         `json:"updated_at" gorm:"autoUpdateTime"`
}

// PaginationData 定义分页响应的结构
type PaginationData struct {
	Total int64 `json:"total" example:"150"`
	Page  int   `json:"page" example:"1"`
	Limit int   `json:"limit" example:"10"`
}
