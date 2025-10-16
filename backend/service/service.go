package service

import (
	"backend/db"
	"backend/models"

	"gorm.io/gorm"
)

type Service struct {
	db *gorm.DB
}

func NewService() *Service {
	return &Service{db: db.GetDB()}
}

func (s *Service) GetOpportunities() ([]models.ArbitrageOpportunity, error) {
	var opportunities []models.ArbitrageOpportunity
	err := s.db.Find(&opportunities).Error
	return opportunities, err
}

func (s *Service) Test() string {
	return "hello"
}
