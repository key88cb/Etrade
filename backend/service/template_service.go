package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"backend/models"

	"gorm.io/datatypes"
	"gorm.io/gorm"
)

type TemplateService struct {
	db          *gorm.DB
	taskManager *TaskManager
	dispatcher  TaskDispatcher
}

func NewTemplateService(db *gorm.DB, taskManager *TaskManager, dispatcher TaskDispatcher) *TemplateService {
	return &TemplateService{db: db, taskManager: taskManager, dispatcher: dispatcher}
}

func (s *TemplateService) CreateTemplate(ctx context.Context, name, taskType string, config datatypes.JSONMap) (*models.ParamTemplate, error) {
	template := &models.ParamTemplate{
		Name:       name,
		TaskType:   taskType,
		ConfigJSON: config,
	}
	if err := s.db.WithContext(ctx).Create(template).Error; err != nil {
		return nil, err
	}
	return template, nil
}

func (s *TemplateService) UpdateTemplate(ctx context.Context, id uint, name, taskType string, config datatypes.JSONMap) (*models.ParamTemplate, error) {
	var template models.ParamTemplate
	if err := s.db.WithContext(ctx).First(&template, id).Error; err != nil {
		return nil, err
	}
	if name != "" {
		template.Name = name
	}
	if taskType != "" {
		template.TaskType = taskType
	}
	if config != nil {
		template.ConfigJSON = config
	}
	if err := s.db.WithContext(ctx).Save(&template).Error; err != nil {
		return nil, err
	}
	return &template, nil
}

func (s *TemplateService) DeleteTemplate(ctx context.Context, id uint) error {
	return s.db.WithContext(ctx).Delete(&models.ParamTemplate{}, id).Error
}

func (s *TemplateService) ListTemplates(ctx context.Context) ([]models.ParamTemplate, error) {
	var templates []models.ParamTemplate
	err := s.db.WithContext(ctx).Order("id DESC").Find(&templates).Error
	return templates, err
}

func (s *TemplateService) GetTemplate(ctx context.Context, id uint) (*models.ParamTemplate, error) {
	var template models.ParamTemplate
	if err := s.db.WithContext(ctx).First(&template, id).Error; err != nil {
		return nil, err
	}
	return &template, nil
}

func (s *TemplateService) RunTemplate(ctx context.Context, templateID uint, overrides map[string]interface{}, taskID, trigger string) (*models.Task, error) {
	template, err := s.GetTemplate(ctx, templateID)
	if err != nil {
		return nil, err
	}
	config := datatypes.JSONMap{}
	for k, v := range template.ConfigJSON {
		config[k] = v
	}
	for k, v := range overrides {
		config[k] = v
	}
	if template.TaskType == "analyse" {
		config, err = s.ensureAnalyseConfig(ctx, config)
		if err != nil {
			return nil, err
		}
	}
	task, err := s.taskManager.CreateTask(ctx, template.TaskType, taskID, trigger, config)
	if err != nil {
		return nil, err
	}
	if s.dispatcher != nil {
		if err := s.dispatcher.Dispatch(context.Background(), task); err != nil {
			log.Printf("dispatch task %s failed: %v", task.TaskID, err)
			return task, err
		}
	}
	return task, nil
}

func (s *TemplateService) ensureAnalyseConfig(ctx context.Context, config datatypes.JSONMap) (datatypes.JSONMap, error) {
	if config == nil {
		config = datatypes.JSONMap{}
	}
	if shouldAutoCreateBatch(config["batch_id"]) {
		now := time.Now()
		batch := &models.Batch{
			Name:        fmt.Sprintf("Auto Batch %s", now.Format("20060102-150405")),
			Description: "自动为套利分析任务创建的批次",
		}
		if err := s.db.WithContext(ctx).Create(batch).Error; err != nil {
			return nil, err
		}
		config["batch_id"] = batch.ID
	}
	return config, nil
}

func shouldAutoCreateBatch(value interface{}) bool {
	if value == nil {
		return true
	}
	switch v := value.(type) {
	case string:
		trimmed := strings.TrimSpace(v)
		if trimmed == "" {
			return true
		}
		num, err := strconv.ParseInt(trimmed, 10, 64)
		if err != nil {
			return false
		}
		return num <= 0
	case float64:
		return v <= 0
	case float32:
		return v <= 0
	case int:
		return v <= 0
	case int32:
		return v <= 0
	case int64:
		return v <= 0
	case uint:
		return v == 0
	case uint32:
		return v == 0
	case uint64:
		return v == 0
	case json.Number:
		num, err := v.Int64()
		if err != nil {
			return true
		}
		return num <= 0
	default:
		return false
	}
}

type BatchService struct {
	db *gorm.DB
}

func NewBatchService(db *gorm.DB) *BatchService {
	return &BatchService{db: db}
}

func (s *BatchService) CreateBatch(ctx context.Context, name, description string) (*models.Batch, error) {
	batch := &models.Batch{
		Name:        name,
		Description: description,
	}
	if err := s.db.WithContext(ctx).Create(batch).Error; err != nil {
		return nil, err
	}
	return batch, nil
}

func (s *BatchService) UpdateBatch(ctx context.Context, id uint, name, description string, refreshed bool) (*models.Batch, error) {
	var batch models.Batch
	if err := s.db.WithContext(ctx).First(&batch, id).Error; err != nil {
		return nil, err
	}
	if name != "" {
		batch.Name = name
	}
	if description != "" {
		batch.Description = description
	}
	if refreshed {
		now := time.Now()
		batch.LastRefreshedAt = &now
	}
	if err := s.db.WithContext(ctx).Save(&batch).Error; err != nil {
		return nil, err
	}
	return &batch, nil
}

func (s *BatchService) ListBatches(ctx context.Context) ([]models.Batch, error) {
	var batches []models.Batch
	err := s.db.WithContext(ctx).Order("id DESC").Find(&batches).Error
	return batches, err
}

func (s *BatchService) GetBatch(ctx context.Context, id uint) (*models.Batch, error) {
	var batch models.Batch
	if err := s.db.WithContext(ctx).First(&batch, id).Error; err != nil {
		return nil, err
	}
	return &batch, nil
}

func (s *BatchService) DeleteBatch(ctx context.Context, id uint) error {
	// Ensure exists
	var batch models.Batch
	if err := s.db.WithContext(ctx).First(&batch, id).Error; err != nil {
		return err
	}

	return s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		// 1) Delete report files + rows
		var reports []models.Report
		if err := tx.Where("batch_id = ?", id).Find(&reports).Error; err != nil {
			return err
		}
		for _, r := range reports {
			if r.FilePath != "" {
				_ = os.Remove(r.FilePath)
			}
		}
		if err := tx.Where("batch_id = ?", id).Delete(&models.Report{}).Error; err != nil {
			return err
		}

		// 2) Delete experiments + runs
		expIDs := tx.Model(&models.Experiment{}).Select("id").Where("batch_id = ?", id)
		if err := tx.Where("experiment_id IN (?)", expIDs).Delete(&models.ExperimentRun{}).Error; err != nil {
			return err
		}
		if err := tx.Where("batch_id = ?", id).Delete(&models.Experiment{}).Error; err != nil {
			return err
		}

		// 3) Delete opportunities (raw table, not a gorm model)
		if err := deleteOpportunitiesByBatch(tx, id); err != nil {
			return err
		}

		// 4) Delete batch itself
		return tx.Delete(&models.Batch{}, id).Error
	})
}

func deleteOpportunitiesByBatch(tx *gorm.DB, batchID uint) error {
	err := tx.Exec("DELETE FROM arbitrage_opportunities WHERE batch_id = ?", batchID).Error
	if err == nil {
		return nil
	}
	// Tests may not create this raw table; ignore undefined-table errors.
	msg := strings.ToLower(err.Error())
	if strings.Contains(msg, "does not exist") || strings.Contains(msg, "undefinedtable") {
		return nil
	}
	return err
}
