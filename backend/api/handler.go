package api

import (
	"backend/models" // 导入 models
	"backend/service"
	"backend/utils"
	"net/http"
	"strconv" // 导入 strconv

	"backend/db"

	"github.com/gin-gonic/gin"
)

// @title        Etrade (CEX-DEX 套利分析平台) API
// @version      1.0
// @description  这是 Etrade v1.0 项目的 SRS API 文档, 实现了 SRS 规范。
// @termsOfService https://github.com/key88cb/Etrade

// @contact.name   项目负责人 Lhb
// @contact.url    https://github.com/key88cb/Etrade

// @license.name  MIT
// @license.url   https://opensource.org/license/mit/

// @host         localhost:8888
// @BasePath     /api/v1
type Handler struct {
	service *service.Service
}

func NewHandler() *Handler {
	return NewHandlerWithService(service.NewService(db.GetDB()))
}

// NewHandlerWithService allows injecting a pre-configured service (used in tests).
func NewHandlerWithService(s *service.Service) *Handler {
	if s == nil {
		panic("service is required")
	}
	return &Handler{service: s}
}

// GetOpportunities
// @Summary      获取套利机会列表 (UC-02)
// @Description  (SRS FR-5.3) 获取套利机会列表，支持分页和排序
// @Tags         Opportunities
// @Accept       json
// @Produce      json
// @Param        page      query      int    false  "页码"                  example(1) default(1)
// @Param        limit     query      int    false  "每页数量"              example(10) default(10)
// @Param        sort_by   query      string false  "排序字段 (snake_case)" example(profit_usdt) default(profit_usdt)
// @Param        order     query      string false  "排序顺序 (asc/desc)"   example(desc) default(desc) Enums(asc, desc)
// @Success      200       {object}   api.SuccessOpportunitiesResponse  "成功响应 (符合 API 规范 3.1.B)"
// @Failure      400       {object}   api.ErrorResponse                 "参数错误 (Code: 40001, 40002)"
// @Failure      500       {object}   api.ErrorResponse                 "服务器内部错误 (Code: 50001)"
// @Router       /opportunities [get]
func (h *Handler) GetOpportunities(c *gin.Context) {
	// --- 解析分页和排序参数 ---
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))
	sortBy := c.DefaultQuery("sort_by", "profit_usdt")
	order := c.DefaultQuery("order", "desc")

	// (简单验证，防止SQL注入)
	if order != "asc" && order != "desc" {
		utils.Fail(c, http.StatusBadRequest, "order 参数必须是 'asc' 或 'desc'")
		return
	}
	// (应该有一个允许的 sortBy 字段白名单)

	// --- service 调用 ---
	opportunities, pagination, err := h.service.GetOpportunities(page, limit, sortBy, order)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return // 增加一个 return
	}

	// --- 成功响应 (符合 API 规范 3.1.B) ---
	utils.Success(c, gin.H{
		"items":      opportunities,
		"pagination": pagination,
	})
}

// GetPriceComparisonData
// @Summary      获取价格对比数据 (UC-01)
// @Description  (SRS FR-5.2) 获取用于 ECharts 渲染的聚合价格数据
// @Tags         Visualization
// @Accept       json
// @Produce      json
// @Param        startTime   query      int    true   "开始时间 (13位毫秒时间戳)"  example(1756694400000)
// @Param        endTime     query      int    true   "结束时间 (13位毫秒时间戳)"  example(1756780799000)
// @Success      200         {object}   api.SuccessPriceResponse  "成功响应 (符合 API 规范 3.1.A)"
// @Failure      400         {object}   api.ErrorResponse         "参数错误 (Code: 40001)"
// @Failure      500         {object}   api.ErrorResponse         "服务器内部错误 (Code: 50001)"
// @Router       /price-comparison [get]
func (h *Handler) GetPriceComparisonData(c *gin.Context) {
	// --- 解析 startTime 和 endTime 参数 ---
	startTimeStr := c.Query("startTime")
	endTimeStr := c.Query("endTime")

	if startTimeStr == "" || endTimeStr == "" {
		utils.Fail(c, http.StatusBadRequest, "startTime 和 endTime 是必选的毫秒时间戳")
		return
	}

	startTime, err1 := strconv.ParseInt(startTimeStr, 10, 64)
	endTime, err2 := strconv.ParseInt(endTimeStr, 10, 64)

	if err1 != nil || err2 != nil {
		utils.Fail(c, http.StatusBadRequest, "startTime 或 endTime 格式错误")
		return
	}

	// 1. 只调用 service，并传入参数
	dataMap, err := h.service.GetPriceComparisonData(startTime, endTime)

	// 2. 处理错误
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}

	// 3. 返回成功响应
	utils.Success(c, dataMap)
}

// 定义用于 Swag 文档的响应结构体---

// PriceDataPoint ECharts 数据点 [timestamp, price]
// Swag 不支持 [2]interface{}, 我们使用一个内部 struct
type PriceDataPoint [2]interface{} // [1756694460000, 3001.5]

// PriceComparisonResponse 价格对比接口的 data 字段
type PriceComparisonResponse struct {
	Uniswap []PriceDataPoint `json:"uniswap"`
	Binance []PriceDataPoint `json:"binance"`
}

// SuccessPriceResponse 价格对比接口的成功响应
type SuccessPriceResponse struct {
	Code    int                     `json:"code" example:"0"`
	Data    PriceComparisonResponse `json:"data"`
	Message string                  `json:"message" example:"success"`
}

// PaginationData 分页信息 (符合 API 规范 3.1.B)
type PaginationData struct {
	Total int64 `json:"total" example:"150"`
	Page  int   `json:"page" example:"1"`
	Limit int   `json:"limit" example:"10"`
}

// OpportunitiesResponse 套利机会接口的 data 字段
type OpportunitiesResponse struct {
	Items      []models.ArbitrageOpportunity `json:"items"`
	Pagination PaginationData                `json:"pagination"`
}

// SuccessOpportunitiesResponse 套利机会接口的成功响应
type SuccessOpportunitiesResponse struct {
	Code    int                   `json:"code" example:"0"`
	Data    OpportunitiesResponse `json:"data"`
	Message string                `json:"message" example:"success"`
}

// ErrorResponse 统一的错误响应 (符合 API 规范 3.2)
type ErrorResponse struct {
	Code    int    `json:"code" example:"40001"`
	Message string `json:"message" example:"请求参数无效"`
}
