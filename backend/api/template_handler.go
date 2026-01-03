package api

import (
	"net/http"
	"strconv"

	"backend/models"
	"backend/service"
	"backend/utils"

	"github.com/gin-gonic/gin"
	"gorm.io/datatypes"
)

type TemplateHandler struct {
	service     *service.TemplateService
	taskManager *service.TaskManager
}

func NewTemplateHandler(s *service.TemplateService, tm *service.TaskManager) *TemplateHandler {
	return &TemplateHandler{service: s, taskManager: tm}
}

// Register 注册模板相关路由
func (h *TemplateHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/templates", h.ListTemplates)
	rg.POST("/templates", h.CreateTemplate)
	rg.PUT("/templates/:id", h.UpdateTemplate)
	rg.DELETE("/templates/:id", h.DeleteTemplate)
	rg.POST("/templates/:id/run", h.RunTemplate)
}

type templateRequest struct {
	Name     string                 `json:"name" binding:"required"`
	TaskType string                 `json:"task_type" binding:"required"`
	Config   map[string]interface{} `json:"config"`
}

type runTemplateRequest struct {
	TaskID    string                 `json:"task_id"`
	Trigger   string                 `json:"trigger"`
	Overrides map[string]interface{} `json:"overrides"`
}

// TemplateResponse 模板响应
type TemplateResponse struct {
	ID       uint                   `json:"id"`
	Name     string                 `json:"name"`
	TaskType string                 `json:"task_type"`
	Config   map[string]interface{} `json:"config"`
}

// ListTemplates 模板列表
// @Summary      模板列表
// @Description  查询所有任务模板
// @Tags         Template
// @Produce      json
// @Success      200  {array}   models.ParamTemplate
// @Router       /templates [get]
func (h *TemplateHandler) ListTemplates(c *gin.Context) {
	templates, err := h.service.ListTemplates(c.Request.Context())
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	resp := make([]TemplateResponse, 0, len(templates))
	for _, tpl := range templates {
		resp = append(resp, toTemplateResponse(tpl))
	}
	utils.Success(c, resp)
}

// CreateTemplate 创建模板
// @Summary      创建模板
// @Tags         Template
// @Accept       json
// @Produce      json
// @Param        template body templateRequest true "模板信息"
// @Success      200      {object} models.ParamTemplate
// @Router       /templates [post]
func (h *TemplateHandler) CreateTemplate(c *gin.Context) {
	var req templateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	template, err := h.service.CreateTemplate(c.Request.Context(), req.Name, req.TaskType, datatypes.JSONMap(req.Config))
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, toTemplateResponse(*template))
}

// UpdateTemplate 更新模板
// @Summary      更新模板
// @Tags         Template
// @Accept       json
// @Produce      json
// @Param        id path int true "模板 ID"
// @Param        template body templateRequest true "模板信息"
// @Success      200 {object} models.ParamTemplate
// @Router       /templates/{id} [put]
func (h *TemplateHandler) UpdateTemplate(c *gin.Context) {
	var req templateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	template, err := h.service.UpdateTemplate(c.Request.Context(), id, req.Name, req.TaskType, datatypes.JSONMap(req.Config))
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, toTemplateResponse(*template))
}

// DeleteTemplate 删除模板
// @Summary      删除模板
// @Tags         Template
// @Param        id path int true "模板 ID"
// @Success      200 {object} map[string]string
// @Router       /templates/{id} [delete]
func (h *TemplateHandler) DeleteTemplate(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	if err := h.service.DeleteTemplate(c.Request.Context(), id); err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, gin.H{"message": "deleted"})
}

// RunTemplate 根据模板创建任务
// @Summary 运行模板
// @Tags    Template
// @Accept  json
// @Produce json
// @Param   id path int true "模板 ID"
// @Param   body body runTemplateRequest false "覆盖参数"
// @Success 200 {object} api.TaskDetailResponse
// @Router  /templates/{id}/run [post]
func (h *TemplateHandler) RunTemplate(c *gin.Context) {
	id, err := parseUintParam(c, "id")
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	var req runTemplateRequest
	if err := c.ShouldBindJSON(&req); err != nil && err.Error() != "EOF" {
		utils.Fail(c, http.StatusBadRequest, err.Error())
		return
	}
	task, err := h.service.RunTemplate(c.Request.Context(), id, req.Overrides, req.TaskID, req.Trigger)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	utils.Success(c, TaskDetailResponse{
		TaskID: task.TaskID,
		Type:   task.Type,
		Status: task.Status,
		Config: task.ConfigJSON,
	})
}

func parseUintParam(c *gin.Context, key string) (uint, error) {
	value := c.Param(key)
	id64, err := strconv.ParseUint(value, 10, 64)
	if err != nil {
		return 0, err
	}
	return uint(id64), nil
}

func toTemplateResponse(tpl models.ParamTemplate) TemplateResponse {
	cfg := map[string]interface{}{}
	for k, v := range tpl.ConfigJSON {
		cfg[k] = v
	}
	return TemplateResponse{
		ID:       tpl.ID,
		Name:     tpl.Name,
		TaskType: tpl.TaskType,
		Config:   cfg,
	}
}
