package db

import (
	"fmt"
	"net"
	"path/filepath"
	"testing"

	embeddedpostgres "github.com/fergusstrange/embedded-postgres"
	"github.com/spf13/viper"
	"github.com/stretchr/testify/require"
)

func startEmbeddedPostgres(t *testing.T) (func(), int) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	port := ln.Addr().(*net.TCPAddr).Port
	_ = ln.Close()

	root := t.TempDir()
	cfg := embeddedpostgres.DefaultConfig().
		Username("postgres").
		Password("postgres").
		Database("testdb").
		Port(uint32(port)).
		Locale("C").
		RuntimePath(filepath.Join(root, "runtime")).
		DataPath(filepath.Join(root, "data")).
		BinariesPath(filepath.Join(root, "bin"))

	pg := embeddedpostgres.NewDatabase(cfg)
	require.NoError(t, pg.Start())

	return func() { _ = pg.Stop() }, port
}

func resetDBState(t *testing.T) {
	t.Helper()
	if database != nil {
		sqlDB, _ := database.DB()
		if sqlDB != nil {
			_ = sqlDB.Close()
		}
		database = nil
	}
	viper.Reset()
}

func TestInitDBSuccess(t *testing.T) {
	t.Cleanup(func() { resetDBState(t) })
	stop, port := startEmbeddedPostgres(t)
	defer stop()

	viper.Set("db.host", "127.0.0.1")
	viper.Set("db.port", fmt.Sprintf("%d", port))
	viper.Set("db.username", "postgres")
	viper.Set("db.password", "postgres")
	viper.Set("db.database", "testdb")

	require.NoError(t, InitDB())
	require.NotNil(t, GetDB())
}

func TestInitDBReturnsErrorWhenServerUnavailable(t *testing.T) {
	t.Cleanup(func() { resetDBState(t) })
	viper.Set("db.host", "127.0.0.1")
	viper.Set("db.port", "65530")
	viper.Set("db.username", "postgres")
	viper.Set("db.password", "postgres")
	viper.Set("db.database", "missing")

	err := InitDB()
	require.Error(t, err)
}

func TestGetDBPanicsWhenNotInitialized(t *testing.T) {
	t.Cleanup(func() { resetDBState(t) })
	database = nil
	require.Panics(t, func() {
		_ = GetDB()
	})
}
