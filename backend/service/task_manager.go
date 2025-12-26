package service

import (
	"context"
	"errors"
	"fmt"
	"log"
	"time"

	"backend/models"

	"github.com/google/uuid"
	"gorm.io/datatypes"
	"gorm.io/gorm"
)

const (
	defaultTaskStatusRunning = "RUNNING"
)

// TaskManager 提供任务的读写能力，任务状态由外部脚本更新，我们只负责落库与查询
type TaskManager struct {
	db *gorm.DB
}

func NewTaskManager(db *gorm.DB) *TaskManager {
	return &TaskManager{db: db}
}

// CreateTask 根据 taskType 和配置创建数据库记录，如果外部未给 taskID 则自动生成
func (m *TaskManager) CreateTask(ctx context.Context, taskType, taskID, trigger string, config datatypes.JSONMap) (*models.Task, error) {
	if taskType == "" {
		return nil, errors.New("task type is required")
	}
	if taskID == "" {
		taskID = uuid.NewString()
	}
	task := &models.Task{
		TaskID:     taskID,
		Type:       taskType,
		ConfigJSON: config,
		Status:     defaultTaskStatusRunning,
		Trigger:    trigger,
		QueuedAt:   ptrTime(time.Now()),
	}
	if err := m.db.WithContext(ctx).Create(task).Error; err != nil {
		log.Printf("[TaskManager] create task failed type=%s id=%s error=%v", taskType, taskID, err)
		return nil, err
	}
	log.Printf("[TaskManager] queued task type=%s id=%s trigger=%s", taskType, taskID, trigger)
	return task, nil
}

// GetTaskByExternalID 根据 TaskID (对外 ID) 查询任务
func (m *TaskManager) GetTaskByExternalID(ctx context.Context, externalID string) (*models.Task, error) {
	var task models.Task
	if err := m.db.WithContext(ctx).Where("task_id = ?", externalID).First(&task).Error; err != nil {
		return nil, err
	}
	return &task, nil
}

// ListTasks 返回分页任务列表
func (m *TaskManager) ListTasks(ctx context.Context, page, limit int) ([]models.Task, int64, error) {
	if page < 1 {
		page = 1
	}
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	var (
		tasks []models.Task
		total int64
	)
	if err := m.db.WithContext(ctx).Model(&models.Task{}).Count(&total).Error; err != nil {
		return nil, 0, err
	}
	offset := (page - 1) * limit
	err := m.db.WithContext(ctx).Order("id DESC").Limit(limit).Offset(offset).Find(&tasks).Error
	return tasks, total, err
}

func (m *TaskManager) ListTaskLogs(ctx context.Context, taskID uint, limit, offset int) ([]models.TaskLog, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	var logs []models.TaskLog
	err := m.db.WithContext(ctx).
		Where("task_id = ?", taskID).
		Order("timestamp ASC").
		Limit(limit).
		Offset(offset).
		Find(&logs).Error
	return logs, err
}

func (m *TaskManager) AddTaskLog(ctx context.Context, taskInternalID uint, level, message string) error {
	if taskInternalID == 0 {
		return errors.New("task id is required")
	}
	logItem := &models.TaskLog{
		TaskID:    taskInternalID,
		Timestamp: time.Now(),
		Level:     level,
		Message:   message,
	}
	return m.db.WithContext(ctx).Create(logItem).Error
}

// CancelTaskByExternalID 将任务标记为 CANCELLED，并写入一条任务日志（用于前端“取消”按钮）。
// 注意：Worker 会通过轮询 tasks.status 来感知取消并尽快停止。
func (m *TaskManager) CancelTaskByExternalID(ctx context.Context, externalID, reason string) (*models.Task, error) {
	if externalID == "" {
		return nil, errors.New("task id is required")
	}
	var task models.Task
	if err := m.db.WithContext(ctx).Where("task_id = ?", externalID).First(&task).Error; err != nil {
		return nil, err
	}

	// 已完成任务不再改状态，直接返回。
	switch task.Status {
	case "SUCCESS", "FAILED", "CANCELLED":
		return &task, nil
	}

	now := time.Now()
	duration := int64(0)
	if task.StartedAt != nil {
		duration = int64(now.Sub(*task.StartedAt).Seconds())
	} else if task.QueuedAt != nil {
		duration = int64(now.Sub(*task.QueuedAt).Seconds())
	}

	summary := "任务被取消"
	if reason != "" {
		summary = fmt.Sprintf("任务被取消: %s", reason)
	}

	updates := map[string]interface{}{
		"status":           "CANCELLED",
		"finished_at":      &now,
		"duration_seconds": duration,
		"log_summary":      summary,
	}
	if err := m.db.WithContext(ctx).Model(&models.Task{}).Where("id = ?", task.ID).Updates(updates).Error; err != nil {
		return nil, err
	}
	_ = m.AddTaskLog(ctx, task.ID, "INFO", summary)

	if err := m.db.WithContext(ctx).Where("id = ?", task.ID).First(&task).Error; err != nil {
		return nil, err
	}
	return &task, nil
}

func ptrTime(t time.Time) *time.Time {
	return &t
}

// EncodeConfig 将简易 map 转为 JSONMap
func EncodeConfig(pairs map[string]interface{}) datatypes.JSONMap {
	if pairs == nil {
		return datatypes.JSONMap{}
	}
	return datatypes.JSONMap(pairs)
}

// MergeConfig 用于把已有 JSONMap 与新 map 合并
func MergeConfig(origin datatypes.JSONMap, updates map[string]interface{}) datatypes.JSONMap {
	if origin == nil {
		origin = datatypes.JSONMap{}
	}
	for k, v := range updates {
		origin[k] = v
	}
	return origin
}

// FormatDBError 将 gorm.ErrRecordNotFound 转为更易读的错误
func FormatDBError(err error, msg string) error {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return fmt.Errorf("%s: %w", msg, err)
	}
	return err
}
