package testutil

import (
	"fmt"
	"net"
	"path/filepath"
	"testing"

	"backend/models"

	embeddedpostgres "github.com/fergusstrange/embedded-postgres"
	postgresdriver "gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// NewInMemoryDB spins up an ephemeral PostgreSQL instance for isolated tests.
func NewInMemoryDB(t *testing.T) *gorm.DB {
	t.Helper()

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("failed to allocate port: %v", err)
	}
	port := ln.Addr().(*net.TCPAddr).Port
	_ = ln.Close()

	rootDir := t.TempDir()
	runtimePath := filepath.Join(rootDir, "runtime")
	binariesPath := filepath.Join(rootDir, "binaries")
	dataPath := filepath.Join(rootDir, "data")

	pg := embeddedpostgres.NewDatabase(embeddedpostgres.DefaultConfig().
		Username("postgres").
		Password("postgres").
		Database("testdb").
		Port(uint32(port)).
		Locale("C").
		RuntimePath(runtimePath).
		DataPath(dataPath).
		BinariesPath(binariesPath),
	)

	if err := pg.Start(); err != nil {
		t.Fatalf("failed to start embedded postgres: %v", err)
	}

	dsn := fmt.Sprintf("host=127.0.0.1 user=postgres password=postgres dbname=testdb port=%d sslmode=disable", port)

	db, err := gorm.Open(postgresdriver.Open(dsn), &gorm.Config{})
	if err != nil {
		_ = pg.Stop()
		t.Fatalf("failed to open postgres database: %v", err)
	}

	if err := db.AutoMigrate(
		&models.ArbitrageOpportunity{},
		&models.AggregatedPrice{},
		&models.Task{},
		&models.TaskLog{},
		&models.ParamTemplate{},
		&models.Batch{},
		&models.Report{},
		&models.Experiment{},
		&models.ExperimentRun{},
	); err != nil {
		_ = pg.Stop()
		t.Fatalf("failed to migrate schema: %v", err)
	}

	t.Cleanup(func() {
		sqlDB, _ := db.DB()
		if sqlDB != nil {
			_ = sqlDB.Close()
		}
		_ = pg.Stop()
	})

	return db
}
