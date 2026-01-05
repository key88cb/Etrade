package api

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"backend/models"
	"backend/service"
	"backend/testutil"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

type responseEnvelope struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

func invokeJSONHandler(t *testing.T, handler func(*gin.Context), method, target string, body io.Reader, params gin.Params) (*httptest.ResponseRecorder, responseEnvelope) {
	t.Helper()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	req := httptest.NewRequest(method, target, body)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	c.Request = req
	if params != nil {
		c.Params = params
	}

	handler(c)

	var resp responseEnvelope
	require.NoErrorf(t, json.Unmarshal(w.Body.Bytes(), &resp), "unexpected response: %s", w.Body.String())
	return w, resp
}

func decodeData[T any](t *testing.T, data json.RawMessage, out *T) {
	t.Helper()
	require.NoError(t, json.Unmarshal(data, out))
}

func TestTemplateHandlerCRUDAndRun(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	templateSvc := service.NewTemplateService(db, taskManager, nil)
	handler := NewTemplateHandler(templateSvc, taskManager)

	_, resp := invokeJSONHandler(t, handler.ListTemplates, http.MethodGet, "/templates", nil, nil)
	var templates []models.ParamTemplate
	decodeData(t, resp.Data, &templates)
	require.Len(t, templates, 0)

	createPayload := strings.NewReader(`{"name":"Analyse BTC","task_type":"analyse","config":{"pair":"BTCUSDT"}}`)
	_, resp = invokeJSONHandler(t, handler.CreateTemplate, http.MethodPost, "/templates", createPayload, nil)
	var created models.ParamTemplate
	decodeData(t, resp.Data, &created)
	require.NotZero(t, created.ID)
	require.Equal(t, "Analyse BTC", created.Name)

	params := gin.Params{{Key: "id", Value: fmt.Sprintf("%d", created.ID)}}
	updatePayload := strings.NewReader(`{"name":"Analyse ETH","task_type":"analyse","config":{"pair":"ETHUSDT"}}`)
	_, resp = invokeJSONHandler(t, handler.UpdateTemplate, http.MethodPut, fmt.Sprintf("/templates/%d", created.ID), updatePayload, params)
	var updated models.ParamTemplate
	decodeData(t, resp.Data, &updated)
	require.Equal(t, "Analyse ETH", updated.Name)

	runPayload := strings.NewReader(`{"trigger":"unit-test","overrides":{"overwrite":true}}`)
	_, resp = invokeJSONHandler(t, handler.RunTemplate, http.MethodPost, fmt.Sprintf("/templates/%d/run", created.ID), runPayload, params)
	var runResp TaskDetailResponse
	decodeData(t, resp.Data, &runResp)
	require.Equal(t, "analyse", runResp.Type)
	require.NotEmpty(t, runResp.TaskID)
	require.NotNil(t, runResp.Config["batch_id"])

	_, resp = invokeJSONHandler(t, handler.DeleteTemplate, http.MethodDelete, fmt.Sprintf("/templates/%d", created.ID), nil, params)
	require.Equal(t, http.StatusOK, resp.Code)

	_, resp = invokeJSONHandler(t, handler.ListTemplates, http.MethodGet, "/templates", nil, nil)
	decodeData(t, resp.Data, &templates)
	require.Len(t, templates, 0)
}

func TestTemplateHandlerRunTemplateAllowsEmptyBody(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	templateSvc := service.NewTemplateService(db, taskManager, nil)
	handler := NewTemplateHandler(templateSvc, taskManager)

	ctx := context.Background()
	template, err := templateSvc.CreateTemplate(ctx, "Headless", "analyse", datatypes.JSONMap{"strategy": "baseline"})
	require.NoError(t, err)

	params := gin.Params{{Key: "id", Value: fmt.Sprintf("%d", template.ID)}}
	emptyPayload := strings.NewReader("")
	_, resp := invokeJSONHandler(t, handler.RunTemplate, http.MethodPost, fmt.Sprintf("/templates/%d/run", template.ID), emptyPayload, params)

	var detail TaskDetailResponse
	decodeData(t, resp.Data, &detail)
	require.Equal(t, http.StatusOK, resp.Code)
	require.Equal(t, "analyse", detail.Type)
	require.NotEmpty(t, detail.TaskID)
}

func TestBatchHandlerLifecycle(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	batchSvc := service.NewBatchService(db)
	handler := NewBatchHandler(batchSvc)

	createPayload := strings.NewReader(`{"name":"Batch A","description":"first"}`)
	_, resp := invokeJSONHandler(t, handler.CreateBatch, http.MethodPost, "/batches", createPayload, nil)
	var batch models.Batch
	decodeData(t, resp.Data, &batch)
	require.NotZero(t, batch.ID)
	require.Equal(t, "Batch A", batch.Name)

	_, resp = invokeJSONHandler(t, handler.ListBatches, http.MethodGet, "/batches", nil, nil)
	var batches []models.Batch
	decodeData(t, resp.Data, &batches)
	require.Len(t, batches, 1)

	params := gin.Params{{Key: "id", Value: fmt.Sprintf("%d", batch.ID)}}
	_, resp = invokeJSONHandler(t, handler.GetBatch, http.MethodGet, fmt.Sprintf("/batches/%d", batch.ID), nil, params)
	var fetched models.Batch
	decodeData(t, resp.Data, &fetched)
	require.Equal(t, batch.ID, fetched.ID)

	updatePayload := strings.NewReader(`{"name":"Batch B","description":"updated","refreshed":true}`)
	_, resp = invokeJSONHandler(t, handler.UpdateBatch, http.MethodPut, fmt.Sprintf("/batches/%d", batch.ID), updatePayload, params)
	var updated models.Batch
	decodeData(t, resp.Data, &updated)
	require.Equal(t, "Batch B", updated.Name)
	require.NotNil(t, updated.LastRefreshedAt)

	_, resp = invokeJSONHandler(t, handler.DeleteBatch, http.MethodDelete, fmt.Sprintf("/batches/%d", batch.ID), nil, params)
	require.Equal(t, http.StatusOK, resp.Code)

	_, resp = invokeJSONHandler(t, handler.GetBatch, http.MethodGet, fmt.Sprintf("/batches/%d", batch.ID), nil, params)
	require.Equal(t, http.StatusNotFound, resp.Code)
}

func TestTaskHandlerEndpoints(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	handler := NewTaskHandler(taskManager)

	ctx := context.Background()
	task, err := taskManager.CreateTask(ctx, "collect_binance", "task-ext-1", "unit-test", service.EncodeConfig(map[string]interface{}{"chunk_size": 1000}))
	require.NoError(t, err)
	require.NoError(t, taskManager.AddTaskLog(ctx, task.ID, "INFO", "queued"))

	_, resp := invokeJSONHandler(t, handler.ListTasks, http.MethodGet, "/tasks?page=1&limit=5", nil, nil)
	var listResp ListTasksResponse
	decodeData(t, resp.Data, &listResp)
	require.Len(t, listResp.Items, 1)
	require.Equal(t, task.TaskID, listResp.Items[0].TaskID)

	params := gin.Params{{Key: "task_id", Value: task.TaskID}}
	_, resp = invokeJSONHandler(t, handler.GetTask, http.MethodGet, fmt.Sprintf("/tasks/%s", task.TaskID), nil, params)
	var detail TaskDetailResponse
	decodeData(t, resp.Data, &detail)
	require.Equal(t, task.TaskID, detail.TaskID)

	_, resp = invokeJSONHandler(t, handler.ListLogs, http.MethodGet, fmt.Sprintf("/tasks/%s/logs?limit=10", task.TaskID), nil, params)
	var logs TaskLogResponse
	decodeData(t, resp.Data, &logs)
	require.Len(t, logs.Items, 1)
	require.Equal(t, "queued", logs.Items[0].Message)

	cancelPayload := strings.NewReader(`{"reason":"no longer needed"}`)
	_, resp = invokeJSONHandler(t, handler.CancelTask, http.MethodPost, fmt.Sprintf("/tasks/%s/cancel", task.TaskID), cancelPayload, params)
	decodeData(t, resp.Data, &detail)
	require.Equal(t, "CANCELLED", detail.Status)
}

func TestTaskHandlerCancelTaskAllowsEmptyBody(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	handler := NewTaskHandler(taskManager)

	ctx := context.Background()
	task, err := taskManager.CreateTask(ctx, "collect_binance", "cancel-empty", "unit-test", service.EncodeConfig(nil))
	require.NoError(t, err)

	params := gin.Params{{Key: "task_id", Value: task.TaskID}}
	emptyPayload := strings.NewReader("")
	_, resp := invokeJSONHandler(t, handler.CancelTask, http.MethodPost, fmt.Sprintf("/tasks/%s/cancel", task.TaskID), emptyPayload, params)

	var detail TaskDetailResponse
	decodeData(t, resp.Data, &detail)
	require.Equal(t, http.StatusOK, resp.Code)
	require.Equal(t, "CANCELLED", detail.Status)
}

func TestExperimentHandlerLifecycle(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	templateSvc := service.NewTemplateService(db, taskManager, nil)
	experimentSvc := service.NewExperimentService(db, templateSvc, taskManager)
	handler := NewExperimentHandler(experimentSvc)

	ctx := context.Background()
	batchSvc := service.NewBatchService(db)
	batch, err := batchSvc.CreateBatch(ctx, "Batch-Exp", "experiment batch")
	require.NoError(t, err)

	template, err := templateSvc.CreateTemplate(ctx, "Analyse", "analyse", datatypes.JSONMap{"strategy": "baseline"})
	require.NoError(t, err)

	createPayload := strings.NewReader(fmt.Sprintf(`{"batch_id":%d,"description":"smoke"}`, batch.ID))
	_, resp := invokeJSONHandler(t, handler.CreateExperiment, http.MethodPost, "/experiments", createPayload, nil)
	var experiment models.Experiment
	decodeData(t, resp.Data, &experiment)
	require.Equal(t, batch.ID, experiment.BatchID)

	_, resp = invokeJSONHandler(t, handler.ListExperiments, http.MethodGet, fmt.Sprintf("/experiments?batch_id=%d", batch.ID), nil, nil)
	var experiments []models.Experiment
	decodeData(t, resp.Data, &experiments)
	require.Len(t, experiments, 1)

	params := gin.Params{{Key: "id", Value: fmt.Sprintf("%d", experiment.ID)}}
	_, resp = invokeJSONHandler(t, handler.GetExperiment, http.MethodGet, fmt.Sprintf("/experiments/%d", experiment.ID), nil, params)
	var detail struct {
		Experiment models.Experiment      `json:"experiment"`
		Runs       []models.ExperimentRun `json:"runs"`
	}
	decodeData(t, resp.Data, &detail)
	require.Equal(t, experiment.ID, detail.Experiment.ID)
	require.Len(t, detail.Runs, 0)

	runPayload := strings.NewReader(fmt.Sprintf(`{"template_id":%d,"trigger":"manual","overrides":{"overwrite":true}}`, template.ID))
	_, resp = invokeJSONHandler(t, handler.RunTemplate, http.MethodPost, fmt.Sprintf("/experiments/%d/runs", experiment.ID), runPayload, params)
	var runResp struct {
		Run  models.ExperimentRun `json:"run"`
		Task models.Task          `json:"task"`
	}
	decodeData(t, resp.Data, &runResp)
	require.Equal(t, experiment.ID, runResp.Run.ExperimentID)
	require.Equal(t, template.ID, runResp.Run.TemplateID)
	require.Equal(t, "analyse", runResp.Task.Type)

	_, resp = invokeJSONHandler(t, handler.ListRuns, http.MethodGet, fmt.Sprintf("/experiments/%d/runs", experiment.ID), nil, params)
	var runs []models.ExperimentRun
	decodeData(t, resp.Data, &runs)
	require.Len(t, runs, 1)
}

func TestReportHandlerEndpoints(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	reportSvc := service.NewReportService(db)
	handler := NewReportHandler(reportSvc)
	ctx := context.Background()

	invalidPayload := strings.NewReader(`{"batch_id":0}`)
	_, resp := invokeJSONHandler(t, handler.CreateReport, http.MethodPost, "/reports", invalidPayload, nil)
	require.Equal(t, http.StatusBadRequest, resp.Code)

	validPayload := strings.NewReader(`{"batch_id":9,"format":"pdf"}`)
	_, createResp := invokeJSONHandler(t, handler.CreateReport, http.MethodPost, "/reports", validPayload, nil)
	require.Equal(t, http.StatusOK, createResp.Code)

	var createdReport models.Report
	decodeData(t, createResp.Data, &createdReport)
	require.NotZero(t, createdReport.ID)

	require.Eventually(t, func() bool {
		var refreshed models.Report
		if err := db.WithContext(ctx).First(&refreshed, createdReport.ID).Error; err != nil {
			return false
		}
		return refreshed.Status == "SUCCESS"
	}, 5*time.Second, 100*time.Millisecond)

	report, err := reportSvc.CreateReport(ctx, 7, 1, "pdf", "")
	require.NoError(t, err)

	tmpDir := t.TempDir()
	filePath := filepath.Join(tmpDir, "report.pdf")
	require.NoError(t, os.WriteFile(filePath, []byte("pdf-body"), 0o644))
	require.NoError(t, db.Model(&models.Report{}).Where("id = ?", report.ID).Updates(map[string]interface{}{"status": "SUCCESS", "file_path": filePath}).Error)

	_, resp = invokeJSONHandler(t, handler.ListReports, http.MethodGet, fmt.Sprintf("/reports?batch_id=%d", report.BatchID), nil, nil)
	var reports []models.Report
	decodeData(t, resp.Data, &reports)
	require.Len(t, reports, 1)

	downloadParams := gin.Params{{Key: "id", Value: fmt.Sprintf("%d", report.ID)}}
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodGet, fmt.Sprintf("/reports/%d/download", report.ID), nil)
	c.Request = req
	c.Params = downloadParams
	handler.DownloadReport(c)
	require.Equal(t, http.StatusOK, w.Code)
	require.Equal(t, "application/octet-stream", w.Header().Get("Content-Type"))
	require.Equal(t, []byte("pdf-body"), w.Body.Bytes())

	_, resp = invokeJSONHandler(t, handler.DeleteReport, http.MethodDelete, fmt.Sprintf("/reports/%d", report.ID), nil, downloadParams)
	require.Equal(t, http.StatusOK, resp.Code)
	_, err = os.Stat(filePath)
	require.Error(t, err)
	require.True(t, os.IsNotExist(err))
}
