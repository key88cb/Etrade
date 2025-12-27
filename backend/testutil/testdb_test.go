package testutil

import (
	"testing"

	"backend/models"

	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

func TestNewInMemoryDBCreatesPostgresInstance(t *testing.T) {
	db := NewInMemoryDB(t)

	require.NoError(t, db.Exec("SELECT 1").Error)

	task := &models.Task{
		TaskID:     "unit",
		Type:       "test",
		Status:     "RUNNING",
		ConfigJSON: datatypes.JSONMap{"k": "v"},
	}
	require.NoError(t, db.Create(task).Error)
	require.NotZero(t, task.ID)
}
