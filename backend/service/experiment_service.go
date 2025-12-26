package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"backend/models"

	"gorm.io/datatypes"
	"gorm.io/gorm"
)

type ExperimentService struct {
	db          *gorm.DB
	templates   *TemplateService
	taskManager *TaskManager
}

func NewExperimentService(db *gorm.DB, templates *TemplateService, taskManager *TaskManager) *ExperimentService {
	return &ExperimentService{
		db:          db,
		templates:   templates,
		taskManager: taskManager,
	}
}

func (s *ExperimentService) CreateExperiment(ctx context.Context, batchID uint, description string) (*models.Experiment, error) {
	if batchID == 0 {
		return nil, errors.New("batch_id is required")
	}
	exp := &models.Experiment{
		BatchID:     batchID,
		Description: description,
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}
	if err := s.db.WithContext(ctx).Create(exp).Error; err != nil {
		return nil, err
	}
	return exp, nil
}

func (s *ExperimentService) ListExperiments(ctx context.Context, batchID uint) ([]models.Experiment, error) {
	var exps []models.Experiment
	tx := s.db.WithContext(ctx).Order("id DESC")
	if batchID > 0 {
		tx = tx.Where("batch_id = ?", batchID)
	}
	if err := tx.Find(&exps).Error; err != nil {
		return nil, err
	}
	return exps, nil
}

func (s *ExperimentService) GetExperiment(ctx context.Context, id uint) (*models.Experiment, error) {
	var exp models.Experiment
	if err := s.db.WithContext(ctx).First(&exp, id).Error; err != nil {
		return nil, err
	}
	return &exp, nil
}

func (s *ExperimentService) ListRuns(ctx context.Context, experimentID uint) ([]models.ExperimentRun, error) {
	if experimentID == 0 {
		return nil, errors.New("experiment id is required")
	}
	var runs []models.ExperimentRun
	err := s.db.WithContext(ctx).
		Where("experiment_id = ?", experimentID).
		Order("id DESC").
		Find(&runs).Error
	return runs, err
}

// RunTemplateInExperiment 运行模板并记录为 ExperimentRun。
// 当前实现以“分析任务 analyse”为主；对于 analyse，会强制覆盖 batch_id 并注入 experiment_id（用于 Worker 写入 details_json）。
func (s *ExperimentService) RunTemplateInExperiment(
	ctx context.Context,
	experimentID uint,
	templateID uint,
	overrides map[string]interface{},
	taskID string,
	trigger string,
) (*models.ExperimentRun, *models.Task, error) {
	if s.templates == nil || s.taskManager == nil {
		return nil, nil, errors.New("experiment service not initialized")
	}
	exp, err := s.GetExperiment(ctx, experimentID)
	if err != nil {
		return nil, nil, err
	}

	if overrides == nil {
		overrides = map[string]interface{}{}
	}

	template, err := s.templates.GetTemplate(ctx, templateID)
	if err != nil {
		return nil, nil, err
	}

	// 保证 analyse 任务能关联到该实验/批次。
	// - batch_id：强制使用实验的 batch_id（避免模板自身配置跑到别的批次）
	// - experiment_id：用于 Worker 写入 opportunities.details_json
	if template.TaskType == "analyse" {
		overrides["batch_id"] = exp.BatchID
		overrides["experiment_id"] = exp.ID
	} else {
		// 对非 analyse 任务仅保留元信息（方便审计/追踪），不强制 batch_id。
		overrides["experiment_id"] = exp.ID
	}

	task, err := s.templates.RunTemplate(ctx, templateID, overrides, taskID, trigger)
	if err != nil {
		return nil, nil, err
	}

	run := &models.ExperimentRun{
		ExperimentID: exp.ID,
		TemplateID:   templateID,
		TaskID:       task.ID,
		MetricsJSON:  datatypes.JSONMap{},
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}
	if err := s.db.WithContext(ctx).Create(run).Error; err != nil {
		return nil, nil, fmt.Errorf("create experiment run failed: %w", err)
	}
	return run, task, nil
}
