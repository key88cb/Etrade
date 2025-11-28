package api

import (
	"net/http"
	"strconv"

	"backend/service"
	"backend/utils"

	"github.com/gin-gonic/gin"
)

type ReportHandler struct {
	service *service.ReportService
}

func NewReportHandler(s *service.ReportService) *ReportHandler {
	return &ReportHandler{service: s}
}

// Register 注册报告路由
func (h *ReportHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/reports", h.ListReports)
	rg.POST("/reports", h.CreateReport)
}

type reportRequest struct {
	BatchID    uint   `json:"batch_id" binding:"required"`
	TemplateID uint   `json:"template_id"`
	Format     string `json:"format" binding:"required"`
	FilePath   string `json:"file_path"`
}

// ListReports 报告列表
// @Summary 报告列表
// @Tags    Report
// @Produce json
// @Param   batch_id query int false "批次 ID"
// @Success 200 {array} models.Report
// @Router  /reports [get]
func (h *ReportHandler) ListReports(c *gin.Context) {
	batchIDStr := c.Query("batch_id")
	var batchID uint
	if batchIDStr != "" {
		id64, err := strconv.ParseUint(batchIDStr, 10, 64)
		if err != nil {
			utils.Fail(c, http.StatusBadRequest, "invalid batch_id")
			return
		}
		batchID = uint(id64)
	}
	reports, err := h.service.ListReports(c.Request.Context(), batchID)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, reports)
}

// CreateReport 创建报告记录
// @Summary 记录报告生成结果
// @Tags    Report
// @Accept  json
// @Produce json
// @Param   report body reportRequest true "报告参数"
// @Success 200 {object} models.Report
// @Router  /reports [post]
func (h *ReportHandler) CreateReport(c *gin.Context) {
	var req reportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	report, err := h.service.CreateReport(c.Request.Context(), req.BatchID, req.TemplateID, req.Format, req.FilePath)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, report)
}
