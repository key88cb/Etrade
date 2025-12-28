package service

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"backend/models"
	"backend/testutil"

	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
	"gorm.io/gorm"
)

func newTaskManager(t *testing.T) *TaskManager {
	t.Helper()
	return NewTaskManager(testutil.NewInMemoryDB(t))
}

func TestTaskManagerCreateAndQuery(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)

	task, err := mgr.CreateTask(ctx, "collect_binance", "task-1", "trigger", datatypes.JSONMap{"import_percentage": 10})
	require.NoError(t, err)
	require.Equal(t, "task-1", task.TaskID)

	fetched, err := mgr.GetTaskByExternalID(ctx, "task-1")
	require.NoError(t, err)
	require.Equal(t, task.ID, fetched.ID)

	tasks, total, err := mgr.ListTasks(ctx, 0, 0)
	require.NoError(t, err)
	require.Equal(t, int64(1), total)
	require.Len(t, tasks, 1)
}

func TestTaskManagerLogsAndCancel(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)

	task, err := mgr.CreateTask(ctx, "collect_binance", "task-logs", "trigger", datatypes.JSONMap{})
	require.NoError(t, err)

	require.Error(t, mgr.AddTaskLog(ctx, 0, "INFO", "boom"))
	require.NoError(t, mgr.AddTaskLog(ctx, task.ID, "INFO", "ready"))
	require.NoError(t, mgr.AddTaskLog(ctx, task.ID, "INFO", "go"))

	logs, err := mgr.ListTaskLogs(ctx, task.ID, -1, 0)
	require.NoError(t, err)
	require.Len(t, logs, 2)

	updated, err := mgr.CancelTaskByExternalID(ctx, "task-logs", "user request")
	require.NoError(t, err)
	require.Equal(t, "CANCELLED", updated.Status)
	require.Contains(t, updated.LogSummary, "user request")

	// Calling cancel again should return the same task without error because status is terminal.
	again, err := mgr.CancelTaskByExternalID(ctx, "task-logs", "ignored")
	require.NoError(t, err)
	require.Equal(t, updated.ID, again.ID)
}

func TestTaskManagerCancelRequiresID(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)

	_, err := mgr.CancelTaskByExternalID(ctx, "", "")
	require.Error(t, err)
}

func TestEncodeMergeAndFormatHelpers(t *testing.T) {
	cfg := EncodeConfig(map[string]interface{}{"key": "value"})
	require.Equal(t, "value", cfg["key"])

	merged := MergeConfig(cfg, map[string]interface{}{"key": "new", "extra": 1})
	require.Equal(t, "new", merged["key"])
	require.Equal(t, 1, merged["extra"])

	err := FormatDBError(gorm.ErrRecordNotFound, "missing task")
	require.True(t, errors.Is(err, gorm.ErrRecordNotFound))

	generic := FormatDBError(errors.New("boom"), "wrap")
	require.Error(t, generic)
}

func TestTaskManagerCreateTaskRequiresType(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)
	_, err := mgr.CreateTask(ctx, "", "", "", datatypes.JSONMap{})
	require.EqualError(t, err, "task type is required")
}

func TestTaskManagerListTasksClampsLimit(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)
	for i := 0; i < 30; i++ {
		_, err := mgr.CreateTask(ctx, "collect", fmt.Sprintf("task-%d", i), "trigger", datatypes.JSONMap{})
		require.NoError(t, err)
	}

	list, total, err := mgr.ListTasks(ctx, -5, 10_000)
	require.NoError(t, err)
	require.Equal(t, int64(30), total)
	require.LessOrEqual(t, len(list), 20)
}

func TestTaskManagerListTaskLogsClampsLimit(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)
	task, err := mgr.CreateTask(ctx, "collect", "loggy", "trigger", datatypes.JSONMap{})
	require.NoError(t, err)
	require.NoError(t, mgr.AddTaskLog(ctx, task.ID, "INFO", "first"))
	require.NoError(t, mgr.AddTaskLog(ctx, task.ID, "INFO", "second"))

	logs, err := mgr.ListTaskLogs(ctx, task.ID, 9999, 0)
	require.NoError(t, err)
	require.Len(t, logs, 2)
}

func TestCancelTaskByExternalIDSkipsTerminalStatuses(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)
	finished := &models.Task{TaskID: "finished", Type: "collect", Status: "SUCCESS"}
	require.NoError(t, mgr.db.WithContext(ctx).Create(finished).Error)

	result, err := mgr.CancelTaskByExternalID(ctx, "finished", "ignored")
	require.NoError(t, err)
	require.Equal(t, "SUCCESS", result.Status)
}

func TestCancelTaskByExternalIDUsesStartedAtDuration(t *testing.T) {
	ctx := context.Background()
	mgr := newTaskManager(t)
	started := time.Now().Add(-3 * time.Minute)
	entry := &models.Task{TaskID: "inflight", Type: "collect", Status: "RUNNING", StartedAt: &started}
	require.NoError(t, mgr.db.WithContext(ctx).Create(entry).Error)

	result, err := mgr.CancelTaskByExternalID(ctx, "inflight", "maintenance")
	require.NoError(t, err)
	require.Equal(t, "CANCELLED", result.Status)
	require.Contains(t, result.LogSummary, "maintenance")
	require.Greater(t, result.DurationSeconds, int64(0))
}
