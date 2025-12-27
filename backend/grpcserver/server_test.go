package grpcserver

import (
	"context"
	"encoding/json"
	"testing"

	"backend/models"
	"backend/pkg/taskpb"
	"backend/service"
	"backend/testutil"

	"github.com/stretchr/testify/require"
)

func TestServerRPCsPersistTasks(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	taskMgr := service.NewTaskManager(db)
	srv := New(taskMgr, "grpc-trigger")
	ctx := context.Background()

	t.Run("CollectBinanceGeneratesID", func(t *testing.T) {
		resp, err := srv.CollectBinance(ctx, &taskpb.CollectBinanceRequest{
			ImportPercentage: 75,
			ChunkSize:        0,
		})
		require.NoError(t, err)
		require.NotEmpty(t, resp.TaskId)

		var task models.Task
		require.NoError(t, db.Where("task_id = ?", resp.TaskId).First(&task).Error)
		require.Equal(t, "collect_binance", task.Type)
		require.Equal(t, "grpc-trigger", task.Trigger)
		require.Equal(t, 75, jsonNumberAsInt(task.ConfigJSON["import_percentage"]))
	})

	t.Run("CollectUniswapUsesProvidedID", func(t *testing.T) {
		resp, err := srv.CollectUniswap(ctx, &taskpb.CollectUniswapRequest{
			TaskId:      "fixed-id",
			PoolAddress: "0xpool",
			StartTs:     1,
			EndTs:       2,
		})
		require.NoError(t, err)
		require.Equal(t, "fixed-id", resp.TaskId)

		var task models.Task
		require.NoError(t, db.Where("task_id = ?", resp.TaskId).First(&task).Error)
		require.Equal(t, "collect_uniswap", task.Type)
		require.Equal(t, "0xpool", task.ConfigJSON["pool_address"])
	})

	t.Run("ProcessPricesPersistsOverrides", func(t *testing.T) {
		resp, err := srv.ProcessPrices(ctx, &taskpb.ProcessPricesRequest{
			TaskId:              "prices",
			StartDate:           10,
			EndDate:             20,
			AggregationInterval: "1h",
			Overwrite:           true,
			DbOverrides:         map[string]string{"dsn": "postgres://"},
		})
		require.NoError(t, err)
		require.Equal(t, "prices", resp.TaskId)

		var task models.Task
		require.NoError(t, db.Where("task_id = ?", resp.TaskId).First(&task).Error)
		overrides, ok := task.ConfigJSON["db_overrides"].(map[string]interface{})
		require.True(t, ok)
		require.Equal(t, "postgres://", overrides["dsn"])
	})

	t.Run("AnalyseCarriesStrategy", func(t *testing.T) {
		strategy := map[string]string{"key": "value"}
		payload, err := json.Marshal(strategy)
		require.NoError(t, err)

		resp, err := srv.Analyse(ctx, &taskpb.AnalyseRequest{
			TaskId:       "analyse",
			BatchId:      42,
			Overwrite:    true,
			StrategyJson: string(payload),
		})
		require.NoError(t, err)
		require.Equal(t, "analyse", resp.TaskId)

		var task models.Task
		require.NoError(t, db.Where("task_id = ?", resp.TaskId).First(&task).Error)
		require.Equal(t, string(payload), task.ConfigJSON["strategy_json"])
	})
}

func jsonNumberAsInt(v interface{}) int {
	switch val := v.(type) {
	case float64:
		return int(val)
	case float32:
		return int(val)
	case int:
		return val
	case int64:
		return int(val)
	case json.Number:
		if i, err := val.Int64(); err == nil {
			return int(i)
		}
	}
	return 0
}
