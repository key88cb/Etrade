package service

import (
	"context"
	"time"

	"backend/models"

	"gorm.io/datatypes"
	"gorm.io/gorm"
)

type TemplateService struct {
	db *gorm.DB
}

func NewTemplateService(db *gorm.DB) *TemplateService {
	return &TemplateService{db: db}
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

type ReportService struct {
	db *gorm.DB
}

func NewReportService(db *gorm.DB) *ReportService {
	return &ReportService{db: db}
}

func (s *ReportService) CreateReport(ctx context.Context, batchID, templateID uint, format, filePath string) (*models.Report, error) {
	report := &models.Report{
		BatchID:     batchID,
		TemplateID:  templateID,
		Format:      format,
		FilePath:    filePath,
		GeneratedAt: time.Now(),
	}
	if err := s.db.WithContext(ctx).Create(report).Error; err != nil {
		return nil, err
	}
	return report, nil
}

func (s *ReportService) ListReports(ctx context.Context, batchID uint) ([]models.Report, error) {
	query := s.db.WithContext(ctx).Model(&models.Report{}).Order("generated_at DESC")
	if batchID != 0 {
		query = query.Where("batch_id = ?", batchID)
	}
	var reports []models.Report
	if err := query.Find(&reports).Error; err != nil {
		return nil, err
	}
	return reports, nil
}
