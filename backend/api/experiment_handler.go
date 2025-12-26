package api

import (
	"net/http"
	"strconv"

	"backend/service"
	"backend/utils"

	"github.com/gin-gonic/gin"
)

type ExperimentHandler struct {
	service *service.ExperimentService
}

func NewExperimentHandler(s *service.ExperimentService) *ExperimentHandler {
	return &ExperimentHandler{service: s}
}

func (h *ExperimentHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/experiments", h.ListExperiments)
	rg.POST("/experiments", h.CreateExperiment)
	rg.GET("/experiments/:id", h.GetExperiment)
	rg.GET("/experiments/:id/runs", h.ListRuns)
	rg.POST("/experiments/:id/runs", h.RunTemplate)
}

type createExperimentRequest struct {
	BatchID     uint   `json:"batch_id" binding:"required"`
	Description string `json:"description"`
}

type runInExperimentRequest struct {
	TemplateID uint                   `json:"template_id" binding:"required"`
	TaskID     string                 `json:"task_id"`
	Trigger    string                 `json:"trigger"`
	Overrides  map[string]interface{} `json:"overrides"`
}

// ListExperiments 实验列表
// @Summary      实验列表
// @Description  可按 batch_id 过滤
// @Tags         Experiment
// @Produce      json
// @Param        batch_id  query int false "批次 ID"
// @Success      200 {array} models.Experiment
// @Router       /experiments [get]
func (h *ExperimentHandler) ListExperiments(c *gin.Context) {
	var batchID uint
	if v := c.Query("batch_id"); v != "" {
		id64, err := strconv.ParseUint(v, 10, 64)
		if err != nil {
			utils.Fail(c, http.StatusBadRequest, "invalid batch_id")
			return
		}
		batchID = uint(id64)
	}
	exps, err := h.service.ListExperiments(c.Request.Context(), batchID)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, exps)
}

// CreateExperiment 创建实验
// @Summary      创建实验
// @Tags         Experiment
// @Accept       json
// @Produce      json
// @Param        body body createExperimentRequest true "实验信息"
// @Success      200 {object} models.Experiment
// @Router       /experiments [post]
func (h *ExperimentHandler) CreateExperiment(c *gin.Context) {
	var req createExperimentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	exp, err := h.service.CreateExperiment(c.Request.Context(), req.BatchID, req.Description)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, exp)
}

// GetExperiment 获取实验详情（包含 runs）
// @Summary      实验详情
// @Tags         Experiment
// @Produce      json
// @Param        id path int true "实验 ID"
// @Success      200 {object} map[string]interface{}
// @Router       /experiments/{id} [get]
func (h *ExperimentHandler) GetExperiment(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	exp, err := h.service.GetExperiment(c.Request.Context(), id)
	if err != nil {
		utils.Fail(c, http.StatusNotFound, err.Error())
		return
	}
	runs, err := h.service.ListRuns(c.Request.Context(), exp.ID)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, gin.H{
		"experiment": exp,
		"runs":       runs,
	})
}

// ListRuns 列出某个实验的运行记录
// @Summary      实验运行列表
// @Tags         Experiment
// @Produce      json
// @Param        id path int true "实验 ID"
// @Success      200 {array} models.ExperimentRun
// @Router       /experiments/{id}/runs [get]
func (h *ExperimentHandler) ListRuns(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	runs, err := h.service.ListRuns(c.Request.Context(), id)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, runs)
}

// RunTemplate 在实验内运行模板（生成 Task + ExperimentRun）
// @Summary      运行实验
// @Description  将模板运行记为一次 ExperimentRun，并注入 experiment_id/batch_id
// @Tags         Experiment
// @Accept       json
// @Produce      json
// @Param        id path int true "实验 ID"
// @Param        body body runInExperimentRequest true "运行信息"
// @Success      200 {object} map[string]interface{}
// @Router       /experiments/{id}/runs [post]
func (h *ExperimentHandler) RunTemplate(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	var req runInExperimentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	run, task, err := h.service.RunTemplateInExperiment(c.Request.Context(), id, req.TemplateID, req.Overrides, req.TaskID, req.Trigger)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, gin.H{
		"run":  run,
		"task": task,
	})
}
