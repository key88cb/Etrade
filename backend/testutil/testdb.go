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

type embeddedDatabase interface {
	Start() error
	Stop() error
}

type embeddedWrapper struct {
	inner *embeddedpostgres.EmbeddedPostgres
}

func (w *embeddedWrapper) Start() error {
	return w.inner.Start()
}

func (w *embeddedWrapper) Stop() error {
	return w.inner.Stop()
}

var (
	listenEphemeral = func() (net.Listener, error) {
		return net.Listen("tcp", "127.0.0.1:0")
	}
	newEmbeddedInstance = func(cfg embeddedpostgres.Config) embeddedDatabase {
		return &embeddedWrapper{embeddedpostgres.NewDatabase(cfg)}
	}
	gormOpen = func(dialector gorm.Dialector, opts ...gorm.Option) (*gorm.DB, error) {
		return gorm.Open(dialector, opts...)
	}
	autoMigrateFn = func(db *gorm.DB, models ...interface{}) error {
		return db.AutoMigrate(models...)
	}
	fatalf = func(t *testing.T, format string, args ...interface{}) {
		t.Fatalf(format, args...)
	}
)

// NewInMemoryDB spins up an ephemeral PostgreSQL instance for isolated tests.
func NewInMemoryDB(t *testing.T) *gorm.DB {
	t.Helper()

	ln, err := listenEphemeral()
	if err != nil {
		fatalf(t, "failed to allocate port: %v", err)
	}
	port := ln.Addr().(*net.TCPAddr).Port
	_ = ln.Close()

	rootDir := t.TempDir()
	runtimePath := filepath.Join(rootDir, "runtime")
	binariesPath := filepath.Join(rootDir, "binaries")
	dataPath := filepath.Join(rootDir, "data")

	cfg := embeddedpostgres.DefaultConfig().
		Username("postgres").
		Password("postgres").
		Database("testdb").
		Port(uint32(port)).
		Locale("C").
		RuntimePath(runtimePath).
		DataPath(dataPath).
		BinariesPath(binariesPath)
	pg := newEmbeddedInstance(cfg)

	if err := pg.Start(); err != nil {
		fatalf(t, "failed to start embedded postgres: %v", err)
	}

	dsn := fmt.Sprintf("host=127.0.0.1 user=postgres password=postgres dbname=testdb port=%d sslmode=disable", port)

	db, err := gormOpen(postgresdriver.Open(dsn), &gorm.Config{})
	if err != nil {
		_ = pg.Stop()
		fatalf(t, "failed to open postgres database: %v", err)
	}

	modelsToMigrate := []interface{}{
		&models.ArbitrageOpportunity{},
		&models.AggregatedPrice{},
		&models.Task{},
		&models.TaskLog{},
		&models.ParamTemplate{},
		&models.Batch{},
		&models.Report{},
		&models.Experiment{},
		&models.ExperimentRun{},
	}
	if err := autoMigrateFn(db, modelsToMigrate...); err != nil {
		_ = pg.Stop()
		fatalf(t, "failed to migrate schema: %v", err)
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
