package models

import (
	"time"

	"gorm.io/datatypes"
)

// Task 记录每一个数据处理或分析任务的生命周期
type Task struct {
	TaskID          string            `gorm:"type:varchar(64);uniqueIndex" json:"task_id"`
	ID              uint              `gorm:"primaryKey"`
	Type            string            `gorm:"type:varchar(64);not null"`
	ConfigJSON      datatypes.JSONMap `gorm:"type:jsonb"`
	Status          string            `gorm:"type:varchar(32);not null"`
	Trigger         string            `gorm:"type:varchar(64)"`
	QueuedAt        *time.Time
	StartedAt       *time.Time
	FinishedAt      *time.Time
	DurationSeconds int64  `gorm:"default:0"`
	LogSummary      string `gorm:"type:text"`
	CreatedAt       time.Time
	UpdatedAt       time.Time
}

// TaskLog 保存任务执行过程中的即时日志
type TaskLog struct {
	ID        uint      `gorm:"primaryKey"`
	TaskID    uint      `gorm:"index;not null"`
	Timestamp time.Time `gorm:"index;not null"`
	Level     string    `gorm:"type:varchar(16);not null"`
	Message   string    `gorm:"type:text"`
	CreatedAt time.Time
}

// ParamTemplate 存放聚合、分析等任务的参数模板
type ParamTemplate struct {
	ID         uint              `gorm:"primaryKey"`
	Name       string            `gorm:"type:varchar(128);not null"`
	TaskType   string            `gorm:"type:varchar(64);not null"`
	ConfigJSON datatypes.JSONMap `gorm:"type:jsonb" swaggertype:"object"`
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

// Batch 表示一批套利机会或分析结果的集合
type Batch struct {
	ID              uint   `gorm:"primaryKey"`
	Name            string `gorm:"type:varchar(128);not null"`
	Description     string `gorm:"type:text"`
	LastRefreshedAt *time.Time
	CreatedAt       time.Time
	UpdatedAt       time.Time
}

// Report 记录某个批次的报告文件
type Report struct {
	ID          uint   `gorm:"primaryKey"`
	BatchID     uint   `gorm:"index;not null"`
	TemplateID  uint   `gorm:"index"`
	Format      string `gorm:"type:varchar(16);not null"`
	FilePath    string `gorm:"type:varchar(512);not null"`
	GeneratedAt time.Time
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// Experiment 一组模板运行视作一次实验，便于对比
type Experiment struct {
	ID          uint   `gorm:"primaryKey"`
	BatchID     uint   `gorm:"index;not null"`
	Description string `gorm:"type:text"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// ExperimentRun 记录某次实验中单个模板的运行结果
type ExperimentRun struct {
	ID           uint              `gorm:"primaryKey"`
	ExperimentID uint              `gorm:"index;not null"`
	TemplateID   uint              `gorm:"index"`
	TaskID       uint              `gorm:"index"`
	MetricsJSON  datatypes.JSONMap `gorm:"type:jsonb"`
	CreatedAt    time.Time
	UpdatedAt    time.Time
}
