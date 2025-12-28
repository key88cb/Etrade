package service

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"backend/models"
	"backend/testutil"

	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

type stubDispatcher struct {
	lastTask  *models.Task
	callCount int
	returnErr error
}

func (s *stubDispatcher) Dispatch(ctx context.Context, task *models.Task) error {
	s.callCount++
	s.lastTask = task
	return s.returnErr
}

func TestTemplateServiceCRUDAndRun(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	ctx := context.Background()
	taskManager := NewTaskManager(db)
	dispatcher := &stubDispatcher{}
	svc := NewTemplateService(db, taskManager, dispatcher)

	tpl, err := svc.CreateTemplate(ctx, "Analyse Alpha", "analyse", datatypes.JSONMap{"foo": "bar"})
	require.NoError(t, err)
	require.NotZero(t, tpl.ID)

	fetched, err := svc.GetTemplate(ctx, tpl.ID)
	require.NoError(t, err)
	require.Equal(t, tpl.ID, fetched.ID)

	updated, err := svc.UpdateTemplate(ctx, tpl.ID, "Updated", "", nil)
	require.NoError(t, err)
	require.Equal(t, "Updated", updated.Name)

	templates, err := svc.ListTemplates(ctx)
	require.NoError(t, err)
	require.Len(t, templates, 1)

	task, err := svc.RunTemplate(ctx, tpl.ID, map[string]interface{}{"extra": 1}, "", "unit-test")
	require.NoError(t, err)
	require.NotEmpty(t, task.TaskID)
	require.Equal(t, "analyse", task.Type)
	require.Equal(t, "unit-test", task.Trigger)
	require.True(t, dispatcher.callCount > 0)
	require.Contains(t, dispatcher.lastTask.ConfigJSON, "batch_id")
	require.Equal(t, 1, dispatcher.lastTask.ConfigJSON["extra"])

	dispatcher.returnErr = errors.New("dispatch failed")
	_, err = svc.RunTemplate(ctx, tpl.ID, map[string]interface{}{}, "manual-id", "unit-test")
	require.Error(t, err)

	require.NoError(t, svc.DeleteTemplate(ctx, tpl.ID))
}

func TestShouldAutoCreateBatchCases(t *testing.T) {
	cases := []struct {
		name     string
		value    interface{}
		expected bool
	}{
		{"nil value", nil, true},
		{"empty string", "  ", true},
		{"negative string", "-1", true},
		{"bad string", "abc", false},
		{"zero float", float64(0), true},
		{"positive int", 2, false},
		{"zero uint", uint(0), true},
		{"json number zero", json.Number("0"), true},
		{"json parse error", json.Number("bad"), true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			require.Equal(t, tc.expected, shouldAutoCreateBatch(tc.value))
		})
	}
}

func TestBatchServiceCRUD(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	ctx := context.Background()
	svc := NewBatchService(db)

	batch, err := svc.CreateBatch(ctx, "Batch A", "desc")
	require.NoError(t, err)

	updated, err := svc.UpdateBatch(ctx, batch.ID, "Batch B", "updated", true)
	require.NoError(t, err)
	require.Equal(t, "Batch B", updated.Name)
	require.NotNil(t, updated.LastRefreshedAt)

	batches, err := svc.ListBatches(ctx)
	require.NoError(t, err)
	require.Len(t, batches, 1)

	got, err := svc.GetBatch(ctx, batch.ID)
	require.NoError(t, err)
	require.Equal(t, batch.ID, got.ID)
}
