package api

import (
	"net/http"
	"testing"

	"github.com/gin-gonic/gin"
)

func routeKey(method, path string) string {
	return method + " " + path
}

func assertRouteRegistered(t *testing.T, engine *gin.Engine, method, path string) {
	t.Helper()
	key := routeKey(method, path)
	for _, r := range engine.Routes() {
		if routeKey(r.Method, r.Path) == key {
			return
		}
	}
	t.Fatalf("route %s not found", key)
}

func TestTemplateHandlerRegisterRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/api/v1")
	handler := &TemplateHandler{}

	handler.Register(group)

	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/templates")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/templates")
	assertRouteRegistered(t, router, http.MethodPut, "/api/v1/templates/:id")
	assertRouteRegistered(t, router, http.MethodDelete, "/api/v1/templates/:id")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/templates/:id/run")
}

func TestBatchHandlerRegisterRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/api/v1")
	handler := &BatchHandler{}

	handler.Register(group)

	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/batches")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/batches")
	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/batches/:id")
	assertRouteRegistered(t, router, http.MethodPut, "/api/v1/batches/:id")
	assertRouteRegistered(t, router, http.MethodDelete, "/api/v1/batches/:id")
}

func TestTaskHandlerRegisterRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/api/v1")
	handler := &TaskHandler{}

	handler.Register(group)

	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/tasks")
	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/tasks/:task_id")
	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/tasks/:task_id/logs")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/tasks/:task_id/cancel")
}

func TestReportHandlerRegisterRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/api/v1")
	handler := &ReportHandler{}

	handler.Register(group)

	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/reports")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/reports")
	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/reports/:id/download")
	assertRouteRegistered(t, router, http.MethodDelete, "/api/v1/reports/:id")
}

func TestExperimentHandlerRegisterRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/api/v1")
	handler := &ExperimentHandler{}

	handler.Register(group)

	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/experiments")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/experiments")
	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/experiments/:id")
	assertRouteRegistered(t, router, http.MethodGet, "/api/v1/experiments/:id/runs")
	assertRouteRegistered(t, router, http.MethodPost, "/api/v1/experiments/:id/runs")
}
