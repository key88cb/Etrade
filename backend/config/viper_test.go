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
	root := filepath.Dir(cwd)

	require.NoError(t, os.Chdir(root))
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
