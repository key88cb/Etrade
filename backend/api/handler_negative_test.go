package api

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"backend/service"
	"backend/testutil"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

func newTemplateHandlerForTest(t *testing.T) *TemplateHandler {
	t.Helper()
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	templateSvc := service.NewTemplateService(db, taskManager, nil)
	return NewTemplateHandler(templateSvc, taskManager)
}

func newGinContext(method, path, payload string) (*gin.Context, *httptest.ResponseRecorder) {
	recorder := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(recorder)
	req := httptest.NewRequest(method, path, strings.NewReader(payload))
	if payload != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	c.Request = req
	return c, recorder
}

func TestTemplateHandlerCreateTemplateValidationError(t *testing.T) {
	handler := newTemplateHandlerForTest(t)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodPost, "/templates", strings.NewReader(`{"task_type":"analyse"}`))
	req.Header.Set("Content-Type", "application/json")
	c.Request = req

	handler.CreateTemplate(c)

	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestTemplateHandlerUpdateTemplateInvalidID(t *testing.T) {
	handler := newTemplateHandlerForTest(t)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodPut, "/templates/abc", strings.NewReader(`{"name":"n","task_type":"analyse"}`))
	req.Header.Set("Content-Type", "application/json")
	c.Request = req
	c.Params = gin.Params{{Key: "id", Value: "abc"}}

	handler.UpdateTemplate(c)

	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestTemplateHandlerRunTemplateBadJSON(t *testing.T) {
	handler := newTemplateHandlerForTest(t)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodPost, "/templates/1/run", strings.NewReader("not-json"))
	req.Header.Set("Content-Type", "application/json")
	c.Request = req
	c.Params = gin.Params{{Key: "id", Value: "1"}}

	handler.RunTemplate(c)

	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestReportHandlerDownloadRequiresReadyStatus(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	reportSvc := service.NewReportService(db)
	handler := NewReportHandler(reportSvc)
	ctx := context.Background()
	report, err := reportSvc.CreateReport(ctx, 7, 1, "pdf", "")
	require.NoError(t, err)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodGet, "/reports/1/download", nil)
	c.Request = req
	c.Params = gin.Params{{Key: "id", Value: fmt.Sprintf("%d", report.ID)}}

	handler.DownloadReport(c)

	require.Equal(t, http.StatusBadRequest, w.Code)

	w2 := httptest.NewRecorder()
	c2, _ := gin.CreateTestContext(w2)
	c2.Request = httptest.NewRequest(http.MethodGet, "/reports/bad/download", nil)
	c2.Params = gin.Params{{Key: "id", Value: "bad"}}
	handler.DownloadReport(c2)
	require.Equal(t, http.StatusBadRequest, w2.Code)
}

func TestTaskHandlerCancelTaskBadPayload(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	handler := NewTaskHandler(taskManager)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodPost, "/tasks/task-1/cancel", strings.NewReader("{"))
	req.Header.Set("Content-Type", "application/json")
	c.Request = req
	c.Params = gin.Params{{Key: "task_id", Value: "task-1"}}

	handler.CancelTask(c)

	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestBatchHandlerCreateBatchInvalidJSON(t *testing.T) {
	handler := &BatchHandler{}
	c, w := newGinContext(http.MethodPost, "/batches", "{")
	handler.CreateBatch(c)
	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestBatchHandlerGetBatchInvalidID(t *testing.T) {
	handler := &BatchHandler{}
	c, w := newGinContext(http.MethodGet, "/batches/abc", "")
	c.Params = gin.Params{{Key: "id", Value: "abc"}}
	handler.GetBatch(c)
	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestBatchHandlerUpdateBatchInvalidPayload(t *testing.T) {
	handler := &BatchHandler{}
	c, w := newGinContext(http.MethodPut, "/batches/1", "not-json")
	c.Params = gin.Params{{Key: "id", Value: "1"}}
	handler.UpdateBatch(c)
	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestHandlerGetOpportunitiesRejectsInvalidOrder(t *testing.T) {
	h := &Handler{}
	c, w := newGinContext(http.MethodGet, "/opportunities?order=bad", "")
	h.GetOpportunities(c)
	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestHandlerPriceComparisonValidation(t *testing.T) {
	h := &Handler{}
	ctxMissing, wMissing := newGinContext(http.MethodGet, "/price-comparison", "")
	h.GetPriceComparisonData(ctxMissing)
	require.Equal(t, http.StatusBadRequest, wMissing.Code)

	ctxInvalid, wInvalid := newGinContext(http.MethodGet, "/price-comparison?startTime=abc&endTime=1", "")
	h.GetPriceComparisonData(ctxInvalid)
	require.Equal(t, http.StatusBadRequest, wInvalid.Code)
}

func TestReportHandlerListReportsInvalidBatchID(t *testing.T) {
	h := &ReportHandler{}
	c, w := newGinContext(http.MethodGet, "/reports?batch_id=bad", "")
	h.ListReports(c)
	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestReportHandlerDeleteReportInvalidID(t *testing.T) {
	h := &ReportHandler{}
	c, w := newGinContext(http.MethodDelete, "/reports/bad", "")
	c.Params = gin.Params{{Key: "id", Value: "bad"}}
	h.DeleteReport(c)
	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestExperimentHandlerValidations(t *testing.T) {
	h := &ExperimentHandler{}
	ctxList, wList := newGinContext(http.MethodGet, "/experiments?batch_id=x", "")
	h.ListExperiments(ctxList)
	require.Equal(t, http.StatusBadRequest, wList.Code)

	ctxGet, wGet := newGinContext(http.MethodGet, "/experiments/abc", "")
	ctxGet.Params = gin.Params{{Key: "id", Value: "abc"}}
	h.GetExperiment(ctxGet)
	require.Equal(t, http.StatusBadRequest, wGet.Code)

	ctxRuns, wRuns := newGinContext(http.MethodGet, "/experiments/def/runs", "")
	ctxRuns.Params = gin.Params{{Key: "id", Value: "def"}}
	h.ListRuns(ctxRuns)
	require.Equal(t, http.StatusBadRequest, wRuns.Code)

	ctxRunTemplate, wRunTemplate := newGinContext(http.MethodPost, "/experiments/1/runs", "not-json")
	ctxRunTemplate.Params = gin.Params{{Key: "id", Value: "1"}}
	h.RunTemplate(ctxRunTemplate)
	require.Equal(t, http.StatusBadRequest, wRunTemplate.Code)
}

func TestTaskHandlerNotFoundBranches(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	manager := service.NewTaskManager(db)
	h := NewTaskHandler(manager)

	ctxTask, wTask := newGinContext(http.MethodGet, "/tasks/missing", "")
	ctxTask.Params = gin.Params{{Key: "task_id", Value: "missing"}}
	h.GetTask(ctxTask)
	require.Equal(t, http.StatusNotFound, wTask.Code)

	ctxLogs, wLogs := newGinContext(http.MethodGet, "/tasks/missing/logs", "")
	ctxLogs.Params = gin.Params{{Key: "task_id", Value: "missing"}}
	h.ListLogs(ctxLogs)
	require.Equal(t, http.StatusNotFound, wLogs.Code)
}

func TestParseUintParamHelpers(t *testing.T) {
	ctxBad, _ := gin.CreateTestContext(httptest.NewRecorder())
	ctxBad.Params = gin.Params{{Key: "id", Value: "abc"}}
	_, err := parseUintParam(ctxBad, "id")
	require.Error(t, err)

	ctxGood, _ := gin.CreateTestContext(httptest.NewRecorder())
	ctxGood.Params = gin.Params{{Key: "id", Value: "42"}}
	id, err := parseUintParam(ctxGood, "id")
	require.NoError(t, err)
	require.Equal(t, uint(42), id)
}

func TestTemplateHandlerUpdateTemplateNotFound(t *testing.T) {
	handler := newTemplateHandlerForTest(t)
	c, w := newGinContext(http.MethodPut, "/templates/999", `{"name":"ghost","task_type":"analyse","config":{"pair":"ETHUSDT"}}`)
	c.Params = gin.Params{{Key: "id", Value: "999"}}

	handler.UpdateTemplate(c)

	require.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestTemplateHandlerRunTemplateMissingTemplate(t *testing.T) {
	handler := newTemplateHandlerForTest(t)
	c, w := newGinContext(http.MethodPost, "/templates/999/run", `{"trigger":"manual","overrides":{"overwrite":true}}`)
	c.Params = gin.Params{{Key: "id", Value: "999"}}

	handler.RunTemplate(c)

	require.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestBatchHandlerUpdateBatchNotFound(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	handler := NewBatchHandler(service.NewBatchService(db))
	c, w := newGinContext(http.MethodPut, "/batches/77", `{"name":"missing","description":"ghost","refreshed":true}`)
	c.Params = gin.Params{{Key: "id", Value: "77"}}

	handler.UpdateBatch(c)

	require.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestReportHandlerDeleteReportNotFound(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	handler := NewReportHandler(service.NewReportService(db))
	c, w := newGinContext(http.MethodDelete, "/reports/33", "")
	c.Params = gin.Params{{Key: "id", Value: "33"}}

	handler.DeleteReport(c)

	require.Equal(t, http.StatusInternalServerError, w.Code)
}

func TestExperimentHandlerRunTemplateServiceError(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskManager := service.NewTaskManager(db)
	templateSvc := service.NewTemplateService(db, taskManager, nil)
	experimentSvc := service.NewExperimentService(db, templateSvc, taskManager)
	handler := NewExperimentHandler(experimentSvc)

	c, w := newGinContext(http.MethodPost, "/experiments/555/runs", `{"template_id":1,"trigger":"manual"}`)
	c.Params = gin.Params{{Key: "id", Value: "555"}}

	handler.RunTemplate(c)

	require.Equal(t, http.StatusInternalServerError, w.Code)
}
