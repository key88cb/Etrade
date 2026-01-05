package api

import (
	"errors"
	"net/http"

	"backend/service"
	"backend/utils"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

type BatchHandler struct {
	service *service.BatchService
}

func NewBatchHandler(s *service.BatchService) *BatchHandler {
	return &BatchHandler{service: s}
}

// Register 注册批次路由
func (h *BatchHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/batches", h.ListBatches)
	rg.POST("/batches", h.CreateBatch)
	rg.GET("/batches/:id", h.GetBatch)
	rg.PUT("/batches/:id", h.UpdateBatch)
	rg.DELETE("/batches/:id", h.DeleteBatch)
}

type batchRequest struct {
	Name        string `json:"name" binding:"required"`
	Description string `json:"description"`
	Refreshed   bool   `json:"refreshed"`
}

// ListBatches 批次列表
// @Summary 批次列表
// @Tags    Batch
// @Produce json
// @Success 200 {array} models.Batch
// @Router  /batches [get]
func (h *BatchHandler) ListBatches(c *gin.Context) {
	batches, err := h.service.ListBatches(c.Request.Context())
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, batches)
}

// CreateBatch 创建批次
// @Summary 创建批次
// @Tags    Batch
// @Accept  json
// @Produce json
// @Param   batch body batchRequest true "批次信息"
// @Success 200 {object} models.Batch
// @Router  /batches [post]
func (h *BatchHandler) CreateBatch(c *gin.Context) {
	var req batchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	batch, err := h.service.CreateBatch(c.Request.Context(), req.Name, req.Description)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, batch)
}

// GetBatch 批次详情
// @Summary 批次详情
// @Tags    Batch
// @Produce json
// @Param   id path int true "批次 ID"
// @Success 200 {object} models.Batch
// @Router  /batches/{id} [get]
func (h *BatchHandler) GetBatch(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	batch, err := h.service.GetBatch(c.Request.Context(), id)
	if err != nil {
		utils.Fail(c, http.StatusNotFound, err.Error())
		return
	}
	utils.Success(c, batch)
}

// UpdateBatch 更新批次
// @Summary 更新批次
// @Tags    Batch
// @Accept  json
// @Produce json
// @Param   id path int true "批次 ID"
// @Param   batch body batchRequest true "批次信息"
// @Success 200 {object} models.Batch
// @Router  /batches/{id} [put]
func (h *BatchHandler) UpdateBatch(c *gin.Context) {
	var req batchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	batch, err := h.service.UpdateBatch(c.Request.Context(), id, req.Name, req.Description, req.Refreshed)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, batch)
}

// DeleteBatch 删除批次
// @Summary 删除批次
// @Tags    Batch
// @Param   id path int true "批次 ID"
// @Success 200 {object} map[string]string
// @Router  /batches/{id} [delete]
func (h *BatchHandler) DeleteBatch(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	if err := h.service.DeleteBatch(c.Request.Context(), id); err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			utils.Fail(c, http.StatusNotFound, err.Error())
			return
		}
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, gin.H{"message": "deleted"})
}
