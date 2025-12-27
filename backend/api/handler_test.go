package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"backend/models"
	"backend/service"
	"backend/testutil"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func newTestHandler(t *testing.T) (*Handler, *service.Service) {
	t.Helper()
	db := testutil.NewInMemoryDB(t)
	svc := service.NewService(db)
	return NewHandlerWithService(svc), svc
}

func TestGetOpportunitiesHandlerReturnsPaginatedPayload(t *testing.T) {
	h, svc := newTestHandler(t)
	err := svc.DB().Create(&[]models.ArbitrageOpportunity{
		{ID: 1, ProfitUSDT: 10, BuyPlatform: "Binance", SellPlatform: "Uniswap"},
		{ID: 2, ProfitUSDT: 30, BuyPlatform: "Uniswap", SellPlatform: "Binance"},
	}).Error
	require.NoError(t, err)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/opportunities?page=1&limit=1&sort_by=profit_usdt&order=desc", nil)
	c.Request = req

	h.GetOpportunities(c)

	assert.Equal(t, http.StatusOK, w.Code)

	var resp struct {
		Code int `json:"code"`
		Data struct {
			Items      []models.ArbitrageOpportunity `json:"items"`
			Pagination models.PaginationData         `json:"pagination"`
		} `json:"data"`
	}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))

	assert.Equal(t, http.StatusOK, resp.Code)
	require.Len(t, resp.Data.Items, 1)
	assert.Equal(t, uint(2), resp.Data.Items[0].ID)
	assert.Equal(t, int64(2), resp.Data.Pagination.Total)
}

func TestGetPriceComparisonDataHandlerValidatesParams(t *testing.T) {
	h, _ := newTestHandler(t)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/api/v1/price-comparison", nil)

	h.GetPriceComparisonData(c)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestGetPriceComparisonDataHandlerReturnsSeries(t *testing.T) {
	h, svc := newTestHandler(t)

	start := time.Unix(1_700_000_000, 0).UTC()
	err := svc.DB().Create(&[]models.AggregatedPrice{
		{TimeBucket: start.Add(5 * time.Minute), Source: "Binance", AveragePrice: 2100},
		{TimeBucket: start.Add(10 * time.Minute), Source: "Uniswap", AveragePrice: 2150},
	}).Error
	require.NoError(t, err)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	url := fmt.Sprintf("/api/v1/price-comparison?startTime=%d&endTime=%d", start.UnixMilli(), start.Add(30*time.Minute).UnixMilli())
	c.Request = httptest.NewRequest(http.MethodGet, url, nil)

	h.GetPriceComparisonData(c)
	assert.Equal(t, http.StatusOK, w.Code)

	var resp struct {
		Data map[string][][2]interface{} `json:"data"`
	}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))

	require.Len(t, resp.Data["binance"], 1)
	require.Len(t, resp.Data["uniswap"], 1)
}

func TestGetOpportunitiesRejectsInvalidOrder(t *testing.T) {
	h, _ := newTestHandler(t)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/api/v1/opportunities?order=sideways", nil)

	h.GetOpportunities(c)

	require.Equal(t, http.StatusBadRequest, w.Code)
}

func TestGetPriceComparisonDataHandlerRejectsBadTimestamp(t *testing.T) {
	h, _ := newTestHandler(t)
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/api/v1/price-comparison?startTime=abc&endTime=123", nil)

	h.GetPriceComparisonData(c)

	require.Equal(t, http.StatusBadRequest, w.Code)
}
