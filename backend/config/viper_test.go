package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/spf13/viper"
	"github.com/stretchr/testify/require"
)

func TestReadConfigFileLoadsValues(t *testing.T) {
	viper.Reset()
	cwd, err := os.Getwd()
	require.NoError(t, err)

	tempDir := t.TempDir()
	configDir := filepath.Join(tempDir, "config")
	require.NoError(t, os.MkdirAll(configDir, 0o755))
	require.NoError(t, os.WriteFile(
		filepath.Join(configDir, "config.yaml"),
		[]byte("db:\n  host: localhost\n"),
		0o644,
	))

	require.NoError(t, os.Chdir(tempDir))
	t.Cleanup(func() {
		_ = os.Chdir(cwd)
		viper.Reset()
	})

	require.NoError(t, ReadConfigFile())
	require.Equal(t, "localhost", viper.GetString("db.host"))
}

func TestReadConfigFileFailsWithoutConfigDir(t *testing.T) {
	viper.Reset()
	cwd, err := os.Getwd()
	require.NoError(t, err)
	tempDir := t.TempDir()
	require.NoError(t, os.Chdir(tempDir))
	defer func() {
		_ = os.Chdir(cwd)
		viper.Reset()
	}()

	err = ReadConfigFile()
	require.Error(t, err)
}
