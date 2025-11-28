package api

import (
	"net/http"
	"strconv"
	"time"

	"backend/service"
	"backend/utils"

	"github.com/gin-gonic/gin"
)

type TaskHandler struct {
	taskManager *service.TaskManager
}

func NewTaskHandler(taskManager *service.TaskManager) *TaskHandler {
	return &TaskHandler{taskManager: taskManager}
}

// Register 注册任务相关的 REST 路由
func (h *TaskHandler) Register(rg *gin.RouterGroup) {
	rg.GET("/tasks", h.ListTasks)
	rg.GET("/tasks/:task_id", h.GetTask)
	rg.GET("/tasks/:task_id/logs", h.ListLogs)
}

// TaskPagination 用于 swagger 展示任务分页信息
type TaskPagination struct {
	Total int64 `json:"total"`
	Page  int   `json:"page"`
	Limit int   `json:"limit"`
}

// TaskItem 任务列表项
type TaskItem struct {
	TaskID     string     `json:"task_id"`
	Type       string     `json:"type"`
	Status     string     `json:"status"`
	Trigger    string     `json:"trigger"`
	QueuedAt   *time.Time `json:"queued_at"`
	StartedAt  *time.Time `json:"started_at"`
	FinishedAt *time.Time `json:"finished_at"`
}

// ListTasksResponse 任务列表响应
type ListTasksResponse struct {
	Items      []TaskItem     `json:"items"`
	Pagination TaskPagination `json:"pagination"`
}

// TaskDetailResponse 任务详情响应
type TaskDetailResponse struct {
	TaskID       string                 `json:"task_id"`
	Type         string                 `json:"type"`
	Status       string                 `json:"status"`
	Trigger      string                 `json:"trigger"`
	Config       map[string]interface{} `json:"config"`
	QueuedAt     *time.Time             `json:"queued_at"`
	StartedAt    *time.Time             `json:"started_at"`
	FinishedAt   *time.Time             `json:"finished_at"`
	LogSummary   string                 `json:"log_summary"`
	DurationSecs int64                  `json:"duration_secs"`
}

// TaskLogItem 任务日志条目
type TaskLogItem struct {
	Timestamp time.Time `json:"timestamp"`
	Level     string    `json:"level"`
	Message   string    `json:"message"`
}

// TaskLogResponse 任务日志响应
type TaskLogResponse struct {
	Items []TaskLogItem `json:"items"`
}

// ListTasks 列出任务
// @Summary      任务列表
// @Description  查询任务列表，可分页
// @Tags         Task
// @Produce      json
// @Param        page   query int false "页码" default(1)
// @Param        limit  query int false "每页数量" default(20)
// @Success      200    {object} ListTasksResponse
// @Router       /tasks [get]
func (h *TaskHandler) ListTasks(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	tasks, total, err := h.taskManager.ListTasks(c.Request.Context(), page, limit)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	items := make([]TaskItem, 0, len(tasks))
	for _, t := range tasks {
		items = append(items, TaskItem{
			TaskID:     t.TaskID,
			Type:       t.Type,
			Status:     t.Status,
			Trigger:    t.Trigger,
			QueuedAt:   t.QueuedAt,
			StartedAt:  t.StartedAt,
			FinishedAt: t.FinishedAt,
		})
	}
	utils.Success(c, ListTasksResponse{
		Items: items,
		Pagination: TaskPagination{
			Total: total,
			Page:  page,
			Limit: limit,
		},
	})
}

// GetTask 获取任务详情
// @Summary      任务详情
// @Description  根据 task_id 查询单个任务
// @Tags         Task
// @Produce      json
// @Param        task_id  path string true "任务 ID"
// @Success      200      {object} TaskDetailResponse
// @Router       /tasks/{task_id} [get]
func (h *TaskHandler) GetTask(c *gin.Context) {
	taskID := c.Param("task_id")
	task, err := h.taskManager.GetTaskByExternalID(c.Request.Context(), taskID)
	if err != nil {
		utils.Fail(c, http.StatusNotFound, err.Error())
		return
	}
	utils.Success(c, TaskDetailResponse{
		TaskID:       task.TaskID,
		Type:         task.Type,
		Status:       task.Status,
		Trigger:      task.Trigger,
		Config:       task.ConfigJSON,
		QueuedAt:     task.QueuedAt,
		StartedAt:    task.StartedAt,
		FinishedAt:   task.FinishedAt,
		LogSummary:   task.LogSummary,
		DurationSecs: task.DurationSeconds,
	})
}

// ListLogs 获取任务日志
// @Summary      任务日志
// @Description  查询某个任务的日志
// @Tags         Task
// @Produce      json
// @Param        task_id path string true "任务 ID"
// @Param        limit   query int false "每页条数" default(50)
// @Param        offset  query int false "偏移量" default(0)
// @Success      200     {object} TaskLogResponse
// @Router       /tasks/{task_id}/logs [get]
func (h *TaskHandler) ListLogs(c *gin.Context) {
	taskID := c.Param("task_id")
	task, err := h.taskManager.GetTaskByExternalID(c.Request.Context(), taskID)
	if err != nil {
		utils.Fail(c, http.StatusNotFound, err.Error())
		return
	}
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	logs, err := h.taskManager.ListTaskLogs(c.Request.Context(), task.ID, limit, offset)
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}
	items := make([]TaskLogItem, 0, len(logs))
	for _, log := range logs {
		items = append(items, TaskLogItem{
			Timestamp: log.Timestamp,
			Level:     log.Level,
			Message:   log.Message,
		})
	}
	utils.Success(c, TaskLogResponse{Items: items})
}
