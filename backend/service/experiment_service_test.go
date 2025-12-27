package service

import (
	"context"
	"testing"

	"backend/testutil"

	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

func TestExperimentServiceLifecycle(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	ctx := context.Background()

	taskManager := NewTaskManager(db)
	templateService := NewTemplateService(db, taskManager, nil)
	batchService := NewBatchService(db)
	expService := NewExperimentService(db, templateService, taskManager)

	batch, err := batchService.CreateBatch(ctx, "Batch", "Desc")
	require.NoError(t, err)

	template, err := templateService.CreateTemplate(ctx, "Analyse", "analyse", datatypes.JSONMap{"window": 5})
	require.NoError(t, err)

	exp, err := expService.CreateExperiment(ctx, batch.ID, "first exp")
	require.NoError(t, err)
	require.Equal(t, batch.ID, exp.BatchID)

	experiments, err := expService.ListExperiments(ctx, batch.ID)
	require.NoError(t, err)
	require.Len(t, experiments, 1)

	fetched, err := expService.GetExperiment(ctx, exp.ID)
	require.NoError(t, err)
	require.Equal(t, exp.ID, fetched.ID)

	run, task, err := expService.RunTemplateInExperiment(ctx, exp.ID, template.ID, map[string]interface{}{"foo": "bar"}, "", "trigger")
	require.NoError(t, err)
	require.NotNil(t, run)
	require.NotNil(t, task)
	require.Equal(t, exp.ID, run.ExperimentID)
	require.Equal(t, batch.ID, task.ConfigJSON["batch_id"])
	require.Equal(t, exp.ID, task.ConfigJSON["experiment_id"])

	runs, err := expService.ListRuns(ctx, exp.ID)
	require.NoError(t, err)
	require.Len(t, runs, 1)
}

func TestExperimentServiceValidation(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	ctx := context.Background()

	expService := NewExperimentService(db, nil, nil)
	_, _, err := expService.RunTemplateInExperiment(ctx, 0, 0, nil, "", "")
	require.Error(t, err)

	_, err = expService.ListRuns(ctx, 0)
	require.Error(t, err)
}
