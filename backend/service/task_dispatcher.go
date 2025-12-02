package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"backend/models"
	"backend/pkg/taskpb"
)

// TaskDispatcher 抽象任务分发机制
type TaskDispatcher interface {
	Dispatch(ctx context.Context, task *models.Task) error
}

type GRPCTaskDispatcher struct {
	client  taskpb.TaskServiceClient
	timeout time.Duration
}

func NewGRPCTaskDispatcher(client taskpb.TaskServiceClient) *GRPCTaskDispatcher {
	return &GRPCTaskDispatcher{
		client:  client,
		timeout: 5 * time.Second,
	}
}

func (d *GRPCTaskDispatcher) Dispatch(ctx context.Context, task *models.Task) error {
	if task == nil {
		return errors.New("task is nil")
	}
	if d.client == nil {
		return errors.New("grpc client is nil")
	}
	reqCtx, cancel := context.WithTimeout(ctx, d.timeout)
	defer cancel()

	switch task.Type {
	case "collect_binance":
		importPercentage := int32(asInt64(task.ConfigJSON["import_percentage"]))
		if importPercentage == 0 {
			importPercentage = 100
		}
		chunkSize := int32(asInt64(task.ConfigJSON["chunk_size"]))
		if chunkSize == 0 {
			chunkSize = 1000000
		}
		_, err := d.client.CollectBinance(reqCtx, &taskpb.CollectBinanceRequest{
			TaskId:           task.TaskID,
			ImportPercentage: importPercentage,
			ChunkSize:        chunkSize,
		})
		return err
	case "collect_uniswap":
		startTs := int32(asInt64(task.ConfigJSON["start_ts"]))
		endTs := int32(asInt64(task.ConfigJSON["end_ts"]))
		poolAddress, _ := task.ConfigJSON["pool_address"].(string)
		_, err := d.client.CollectUniswap(reqCtx, &taskpb.CollectUniswapRequest{
			TaskId:      task.TaskID,
			PoolAddress: poolAddress,
			StartTs:     startTs,
			EndTs:       endTs,
		})
		return err
	case "process_prices":
		startDate := int32(parseTimeOrInt(task.ConfigJSON["start_date"]))
		endDate := int32(parseTimeOrInt(task.ConfigJSON["end_date"]))
		aggregationInterval := ""
		if val, ok := task.ConfigJSON["aggregation_interval"]; ok && val != nil {
			aggregationInterval = val.(string)
		}
		overwrite := asBool(task.ConfigJSON["overwrite"])
		dbOverrides := make(map[string]string)
		if val, ok := task.ConfigJSON["db_overrides"]; ok && val != nil {
			if m, ok := val.(map[string]interface{}); ok {
				for k, v := range m {
					if s, ok := v.(string); ok {
						dbOverrides[k] = s
					}
				}
			} else if m, ok := val.(map[string]string); ok {
				dbOverrides = m
			}
		}
		_, err := d.client.ProcessPrices(reqCtx, &taskpb.ProcessPricesRequest{
			TaskId:              task.TaskID,
			StartDate:           startDate,
			EndDate:             endDate,
			AggregationInterval: aggregationInterval,
			Overwrite:           overwrite,
			DbOverrides:         dbOverrides,
		})
		return err
	case "analyse":
		batchID := int32(asInt64(task.ConfigJSON["batch_id"]))
		overwrite := asBool(task.ConfigJSON["overwrite"])
		var strategyJSON string
		if strategy, ok := task.ConfigJSON["strategy"]; ok {
			if data, err := json.Marshal(strategy); err == nil {
				strategyJSON = string(data)
			}
		}
		_, err := d.client.Analyse(reqCtx, &taskpb.AnalyseRequest{
			TaskId:       task.TaskID,
			BatchId:      batchID,
			Overwrite:    overwrite,
			StrategyJson: strategyJSON,
		})
		return err
	default:
		return fmt.Errorf("unsupported task type %s", task.Type)
	}
}

func parseTimeOrInt(v interface{}) int64 {
	if v == nil {
		return 0
	}
	if s, ok := v.(string); ok {
		// 尝试解析 ISO 时间
		if t, err := time.Parse(time.RFC3339, s); err == nil {
			return t.Unix()
		}
		// 尝试解析其他常用格式
		if t, err := time.Parse("2006-01-02T15:04:05", s); err == nil {
			return t.Unix()
		}
	}
	return asInt64(v)
}

func asInt64(v interface{}) int64 {
	switch value := v.(type) {
	case int:
		return int64(value)
	case int32:
		return int64(value)
	case int64:
		return value
	case float32:
		return int64(value)
	case float64:
		return int64(value)
	case json.Number:
		if i, err := value.Int64(); err == nil {
			return i
		}
	case string:
		var n json.Number = json.Number(value)
		if i, err := n.Int64(); err == nil {
			return i
		}
	}
	return 0
}

func asBool(v interface{}) bool {
	switch value := v.(type) {
	case bool:
		return value
	case string:
		return value == "true" || value == "1"
	case float64:
		return value != 0
	case float32:
		return value != 0
	case int, int32, int64:
		return asInt64(v) != 0
	default:
		return false
	}
}
