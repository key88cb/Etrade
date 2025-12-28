package testutil

import (
	"errors"
	"fmt"
	"net"
	"testing"

	"backend/models"

	embeddedpostgres "github.com/fergusstrange/embedded-postgres"
	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
	"gorm.io/gorm"
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

func TestNewInMemoryDBFailureBranches(t *testing.T) {
	expectFatal(t, "listener failure", "failed to allocate port: boom", func(st *testing.T) {
		patchListener(st, errors.New("boom"))
	})

	startFake := &fakeEmbedded{startErr: errors.New("start-fail")}
	expectFatal(t, "postgres start failure", "failed to start embedded postgres: start-fail", func(st *testing.T) {
		patchEmbedded(st, startFake)
	})
	require.Equal(t, 1, startFake.startCalls)
	require.Equal(t, 0, startFake.stopCalls)

	gormFake := &fakeEmbedded{}
	expectFatal(t, "gorm open failure", "failed to open postgres database: open-fail", func(st *testing.T) {
		patchEmbedded(st, gormFake)
		patchGormOpen(st, errors.New("open-fail"))
	})
	require.Equal(t, 1, gormFake.startCalls)
	require.Equal(t, 1, gormFake.stopCalls)

	expectFatal(t, "auto migrate failure", "failed to migrate schema: migrate-fail", func(st *testing.T) {
		patchAutoMigrate(st, errors.New("migrate-fail"))
	})
}

func expectFatal(t *testing.T, name, expectMsg string, setup func(st *testing.T)) {
	t.Helper()
	t.Run(name, func(st *testing.T) {
		patchFatal(st)
		setup(st)
		require.PanicsWithValue(st, expectMsg, func() {
			NewInMemoryDB(st)
		})
	})
}

type fakeEmbedded struct {
	startErr   error
	stopErr    error
	startCalls int
	stopCalls  int
}

func (f *fakeEmbedded) Start() error {
	f.startCalls++
	return f.startErr
}

func (f *fakeEmbedded) Stop() error {
	f.stopCalls++
	return f.stopErr
}

func patchListener(t *testing.T, err error) {
	t.Helper()
	original := listenEphemeral
	listenEphemeral = func() (net.Listener, error) {
		return nil, err
	}
	t.Cleanup(func() { listenEphemeral = original })
}

func patchEmbedded(t *testing.T, fake embeddedDatabase) {
	t.Helper()
	original := newEmbeddedInstance
	newEmbeddedInstance = func(cfg embeddedpostgres.Config) embeddedDatabase {
		return fake
	}
	t.Cleanup(func() { newEmbeddedInstance = original })
}

func patchFatal(t *testing.T) {
	t.Helper()
	original := fatalf
	fatalf = func(tb *testing.T, format string, args ...interface{}) {
		panic(fmt.Sprintf(format, args...))
	}
	t.Cleanup(func() { fatalf = original })
}

func patchGormOpen(t *testing.T, err error) {
	t.Helper()
	original := gormOpen
	gormOpen = func(gorm.Dialector, ...gorm.Option) (*gorm.DB, error) {
		return nil, err
	}
	t.Cleanup(func() { gormOpen = original })
}

func patchAutoMigrate(t *testing.T, err error) {
	t.Helper()
	original := autoMigrateFn
	autoMigrateFn = func(*gorm.DB, ...interface{}) error {
		return err
	}
	t.Cleanup(func() { autoMigrateFn = original })
}
