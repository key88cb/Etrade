package api

import (
	"fmt"
	"net/http"
	"path/filepath"
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

	// 下载接口
	rg.GET("/reports/:id/download", h.DownloadReport)

	// 如果您还需要删除功能
	rg.DELETE("/reports/:id", h.DeleteReport)
}

type reportRequest struct {
	BatchID    uint   `json:"batch_id" binding:"required"`
	TemplateID uint   `json:"template_id"`
	Format     string `json:"format" binding:"required"`
	// FilePath 不需要前端传
}

// ListReports 报告列表
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

// CreateReport 创建并生成报告
func (h *ReportHandler) CreateReport(c *gin.Context) {
	var req reportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}

	// 1. 数据库占位 (Status: PENDING)
	report, err := h.service.CreateReport(c.Request.Context(), req.BatchID, req.TemplateID, req.Format, "")
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}

	// 启动异步协程生成文件
	// 如果没有这一段，状态永远是 Pending
	go func() {
		fmt.Printf("🚀 Starting generation for Report #%d...\n", report.ID)
		err := h.service.GenerateReportFile(report.ID, req.BatchID, req.Format)
		if err != nil {
			fmt.Printf("❌ Failed to generate report %d: %v\n", report.ID, err)
		} else {
			fmt.Printf("✅ Generation complete for Report #%d\n", report.ID)
		}
	}()

	utils.Success(c, report)
}

// DownloadReport 下载报告
func (h *ReportHandler) DownloadReport(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseUint(idStr, 10, 64)
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, "invalid report id")
		return
	}

	// 1. 获取报告详情
	report, err := h.service.GetReport(c.Request.Context(), uint(id))
	if err != nil {
		utils.Fail(c, http.StatusNotFound, "report not found")
		return
	}

	if report.Status != "SUCCESS" {
		utils.Fail(c, http.StatusBadRequest, "report is not ready")
		return
	}

	// 2. 返回文件
	fileName := filepath.Base(report.FilePath)
	c.Header("Content-Disposition", "attachment; filename="+fileName)
	c.Header("Content-Type", "application/octet-stream")
	c.File(report.FilePath)
}

// DeleteReport 删除报告
func (h *ReportHandler) DeleteReport(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseUint(idStr, 10, 64)
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, "invalid report id")
		return
	}
	if err := h.service.DeleteReport(c.Request.Context(), uint(id)); err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, nil)
}
