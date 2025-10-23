// api/handlers.go
package api

import (
	"backend/service"
	"backend/utils"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	service *service.Service
}

func NewHandler() *Handler {
	return &Handler{service: service.NewService()}
}

func (h *Handler) GetOpportunities(c *gin.Context) {
	opportunities, err := h.service.GetOpportunities()
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return // 增加一个 return
	}
	utils.Success(c, opportunities)
}

// GetPriceComparisonData 现在是一个 Handler 的方法
func (h *Handler) GetPriceComparisonData(c *gin.Context) {
	// 1. 只调用 service
	dataMap, err := h.service.GetPriceComparisonData()

	// 2. 处理错误
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}

	// 3. 返回成功响应
	utils.Success(c, dataMap)
}
