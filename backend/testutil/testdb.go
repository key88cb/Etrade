package testutil

import (
	"testing"

	"backend/models"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

// NewInMemoryDB creates a transient SQLite database for tests.
func NewInMemoryDB(t *testing.T) *gorm.DB {
	t.Helper()

	db, err := gorm.Open(sqlite.Open("file::memory:?cache=shared"), &gorm.Config{})
	if err != nil {
		t.Fatalf("failed to open in-memory database: %v", err)
	}

	if err := db.AutoMigrate(
		&models.ArbitrageOpportunity{},
		&models.AggregatedPrice{},
	); err != nil {
		t.Fatalf("failed to migrate schema: %v", err)
	}

	t.Cleanup(func() {
		sqlDB, _ := db.DB()
		if sqlDB != nil {
			_ = sqlDB.Close()
		}
	})

	return db
}
