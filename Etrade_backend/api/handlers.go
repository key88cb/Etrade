package api

import (
	"Etrade_backend/models"
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// GetOpportunities 获取所有套利机会
func GetOpportunities(db *gorm.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		var opportunities []models.ArbitrageOpportunity

		// GORM会在这里查询数据库中的所有记录
		result := db.Find(&opportunities)

		if result.Error != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to retrieve opportunities"})
			return
		}

		c.JSON(http.StatusOK, opportunities)
	}
}
