package service

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"backend/models"
	"backend/pkg/taskpb"

	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"gorm.io/datatypes"
)

type stubTaskClient struct {
	err        error
	binanceReq *taskpb.CollectBinanceRequest
	uniswapReq *taskpb.CollectUniswapRequest
	pricesReq  *taskpb.ProcessPricesRequest
	analyseReq *taskpb.AnalyseRequest
	lastMethod string
}

func (s *stubTaskClient) CollectBinance(ctx context.Context, req *taskpb.CollectBinanceRequest, _ ...grpc.CallOption) (*taskpb.TaskResponse, error) {
	s.lastMethod = "binance"
	s.binanceReq = req
	return &taskpb.TaskResponse{TaskId: req.GetTaskId()}, s.err
}

func (s *stubTaskClient) CollectBinanceByDate(ctx context.Context, req *taskpb.CollectBinanceByDateRequest, _ ...grpc.CallOption) (*taskpb.TaskResponse, error) {
	s.lastMethod = "binance-by-date"
	return &taskpb.TaskResponse{TaskId: req.GetTaskId()}, s.err
}

func (s *stubTaskClient) CollectUniswap(ctx context.Context, req *taskpb.CollectUniswapRequest, _ ...grpc.CallOption) (*taskpb.TaskResponse, error) {
	s.lastMethod = "uniswap"
	s.uniswapReq = req
	return &taskpb.TaskResponse{TaskId: req.GetTaskId()}, s.err
}

func (s *stubTaskClient) ProcessPrices(ctx context.Context, req *taskpb.ProcessPricesRequest, _ ...grpc.CallOption) (*taskpb.TaskResponse, error) {
	s.lastMethod = "prices"
	s.pricesReq = req
	return &taskpb.TaskResponse{TaskId: req.GetTaskId()}, s.err
}

func (s *stubTaskClient) Analyse(ctx context.Context, req *taskpb.AnalyseRequest, _ ...grpc.CallOption) (*taskpb.TaskResponse, error) {
	s.lastMethod = "analyse"
	s.analyseReq = req
	return &taskpb.TaskResponse{TaskId: req.GetTaskId()}, s.err
}

func TestDispatcherValidation(t *testing.T) {
	dispatcher := NewGRPCTaskDispatcher(nil)
	require.Error(t, dispatcher.Dispatch(context.Background(), &models.Task{}))

	dispatcher = &GRPCTaskDispatcher{}
	require.EqualError(t, dispatcher.Dispatch(context.Background(), nil), "task is nil")
}

func TestDispatcherDispatchesByType(t *testing.T) {
	client := &stubTaskClient{}
	dispatcher := NewGRPCTaskDispatcher(client)
	ctx := context.Background()

	binanceTask := &models.Task{TaskID: "bin", Type: "collect_binance", ConfigJSON: datatypes.JSONMap{"import_percentage": 0, "chunk_size": 0}}
	require.NoError(t, dispatcher.Dispatch(ctx, binanceTask))
	require.Equal(t, "binance", client.lastMethod)
	require.EqualValues(t, 100, client.binanceReq.GetImportPercentage())
	require.EqualValues(t, 1000000, client.binanceReq.GetChunkSize())

	uniswapTask := &models.Task{TaskID: "uni", Type: "collect_uniswap", ConfigJSON: datatypes.JSONMap{"pool_address": "pool", "start_ts": 1, "end_ts": 2}}
	require.NoError(t, dispatcher.Dispatch(ctx, uniswapTask))
	require.Equal(t, "uniswap", client.lastMethod)
	require.Equal(t, "pool", client.uniswapReq.GetPoolAddress())

	startISO := time.Unix(1, 0).UTC().Format(time.RFC3339)
	endISO := "2024-01-02T03:04:05"
	pricesTask := &models.Task{TaskID: "prices", Type: "process_prices", ConfigJSON: datatypes.JSONMap{
		"start_date":           startISO,
		"end_date":             endISO,
		"aggregation_interval": "1h",
		"overwrite":            true,
		"db_overrides":         map[string]interface{}{"dsn": "postgres"},
	}}
	require.NoError(t, dispatcher.Dispatch(ctx, pricesTask))
	require.Equal(t, "prices", client.pricesReq.GetTaskId())
	require.Equal(t, int32(1), client.pricesReq.GetStartDate())
	expectedEnd := time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC).Unix()
	require.Equal(t, int32(expectedEnd), client.pricesReq.GetEndDate())

	strategy := map[string]interface{}{"strategy": map[string]interface{}{"window": 5}, "experiment_id": 9}
	analyseTask := &models.Task{TaskID: "analyse", Type: "analyse", ConfigJSON: datatypes.JSONMap(strategy)}
	require.NoError(t, dispatcher.Dispatch(ctx, analyseTask))
	var payload map[string]interface{}
	require.NoError(t, json.Unmarshal([]byte(client.analyseReq.GetStrategyJson()), &payload))
	require.EqualValues(t, 9, payload["experiment_id"])

	unsupported := &models.Task{TaskID: "x", Type: "unknown", ConfigJSON: datatypes.JSONMap{}}
	require.EqualError(t, dispatcher.Dispatch(ctx, unsupported), "unsupported task type unknown")
}

func TestDispatcherProcessPricesWithStringOverrides(t *testing.T) {
	client := &stubTaskClient{}
	dispatcher := &GRPCTaskDispatcher{client: client, timeout: time.Second}
	task := &models.Task{TaskID: "pp-map", Type: "process_prices", ConfigJSON: datatypes.JSONMap{
		"start_date":           int64(10),
		"end_date":             int64(20),
		"aggregation_interval": "5m",
		"db_overrides":         map[string]string{"dsn": "memory"},
	}}
	require.NoError(t, dispatcher.Dispatch(context.Background(), task))
	require.Equal(t, "memory", client.pricesReq.GetDbOverrides()["dsn"])
}

func TestHelperConversions(t *testing.T) {
	require.Equal(t, int64(42), asInt64("42"))
	require.Equal(t, int64(0), asInt64("bad"))
	require.True(t, asBool("true"))
	require.False(t, asBool(0))
	require.True(t, asBool(int64(2)))
	require.True(t, asBool(float32(0.5)))
	require.Equal(t, int64(1700000000), parseTimeOrInt("2023-11-14T22:13:20"))
	require.Equal(t, int64(1700003600), parseTimeOrInt("2023-11-14T23:13:20"))
	require.Equal(t, int64(99), parseTimeOrInt(int64(99)))
}
