package grpcserver

import (
	"context"
	"fmt"
	"net"

	"backend/pkg/taskpb"
	"backend/service"

	"github.com/google/uuid"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"gorm.io/datatypes"
)

type Config struct {
	Port    string
	Trigger string
}

type Server struct {
	taskpb.UnimplementedTaskServiceServer
	taskManager *service.TaskManager
	trigger     string
}

func New(taskManager *service.TaskManager, trigger string) *Server {
	return &Server{
		taskManager: taskManager,
		trigger:     trigger,
	}
}

func (s *Server) CollectBinance(ctx context.Context, req *taskpb.CollectBinanceRequest) (*taskpb.TaskResponse, error) {
	config := map[string]interface{}{
		"import_percentage": req.GetImportPercentage(),
		"chunk_size":        req.GetChunkSize(),
	}
	return s.createTask(ctx, req.GetTaskId(), "collect_binance", config)
}

func (s *Server) CollectUniswap(ctx context.Context, req *taskpb.CollectUniswapRequest) (*taskpb.TaskResponse, error) {
	config := map[string]interface{}{
		"pool_address": req.GetPoolAddress(),
		"start_ts":     req.GetStartTs(),
		"end_ts":       req.GetEndTs(),
	}
	return s.createTask(ctx, req.GetTaskId(), "collect_uniswap", config)
}

func (s *Server) ProcessPrices(ctx context.Context, req *taskpb.ProcessPricesRequest) (*taskpb.TaskResponse, error) {
	config := map[string]interface{}{
		"start_date":           req.GetStartDate(),
		"end_date":             req.GetEndDate(),
		"aggregation_interval": req.GetAggregationInterval(),
		"overwrite":            req.GetOverwrite(),
		"db_overrides":         req.GetDbOverrides(),
	}
	return s.createTask(ctx, req.GetTaskId(), "process_prices", config)
}

func (s *Server) Analyse(ctx context.Context, req *taskpb.AnalyseRequest) (*taskpb.TaskResponse, error) {
	config := map[string]interface{}{
		"batch_id":      req.GetBatchId(),
		"overwrite":     req.GetOverwrite(),
		"strategy_json": req.GetStrategyJson(),
	}
	return s.createTask(ctx, req.GetTaskId(), "analyse", config)
}

func (s *Server) createTask(ctx context.Context, taskID, taskType string, params map[string]interface{}) (*taskpb.TaskResponse, error) {
	if taskID == "" {
		taskID = uuid.NewString()
	}
	config := datatypes.JSONMap{}
	for k, v := range params {
		config[k] = v
	}
	task, err := s.taskManager.CreateTask(ctx, taskType, taskID, s.trigger, config)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "create task failed: %v", err)
	}
	return &taskpb.TaskResponse{
		TaskId: task.TaskID,
		Status: taskpb.TaskStatus_TASK_STATUS_RUNNING,
	}, nil
}

func Run(cfg Config, taskManager *service.TaskManager) error {
	port := cfg.Port
	if port == "" {
		port = ":50051"
	} else if port[0] != ':' {
		port = fmt.Sprintf(":%s", port)
	}
	lis, err := net.Listen("tcp", port)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", port, err)
	}
	srv := grpc.NewServer()
	taskpb.RegisterTaskServiceServer(srv, New(taskManager, cfg.Trigger))
	return srv.Serve(lis)
}
