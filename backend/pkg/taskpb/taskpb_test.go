package taskpb

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protoreflect"
)

type fakeConn struct {
	lastMethod string
	lastOpts   []grpc.CallOption
	errors     map[string]error
}

func (f *fakeConn) Invoke(ctx context.Context, method string, args interface{}, reply interface{}, opts ...grpc.CallOption) error {
	f.lastMethod = method
	f.lastOpts = append([]grpc.CallOption(nil), opts...)
	if err, ok := f.errors[method]; ok {
		return err
	}
	return nil
}

func (f *fakeConn) NewStream(ctx context.Context, desc *grpc.StreamDesc, method string, opts ...grpc.CallOption) (grpc.ClientStream, error) {
	return nil, errors.New("not implemented")
}

func TestTaskServiceClientInvokesMethods(t *testing.T) {
	conn := &fakeConn{}
	client := NewTaskServiceClient(conn)

	_, err := client.CollectBinance(context.Background(), &CollectBinanceRequest{})
	require.NoError(t, err)
	require.Equal(t, TaskService_CollectBinance_FullMethodName, conn.lastMethod)

	_, err = client.CollectUniswap(context.Background(), &CollectUniswapRequest{})
	require.NoError(t, err)
	require.Equal(t, TaskService_CollectUniswap_FullMethodName, conn.lastMethod)

	_, err = client.ProcessPrices(context.Background(), &ProcessPricesRequest{})
	require.NoError(t, err)
	require.Equal(t, TaskService_ProcessPrices_FullMethodName, conn.lastMethod)

	_, err = client.Analyse(context.Background(), &AnalyseRequest{})
	require.NoError(t, err)
	require.Equal(t, TaskService_Analyse_FullMethodName, conn.lastMethod)

	_, err = client.CollectBinanceByDate(context.Background(), &CollectBinanceByDateRequest{})
	require.NoError(t, err)
	require.Equal(t, TaskService_CollectBinanceByDate_FullMethodName, conn.lastMethod)
}

func TestTaskServiceClientPropagatesErrorsAndOptions(t *testing.T) {
	boom := errors.New("invoke failure")
	conn := &fakeConn{errors: map[string]error{
		TaskService_ProcessPrices_FullMethodName: boom,
	}}
	client := NewTaskServiceClient(conn)
	opts := []grpc.CallOption{grpc.WaitForReady(true)}
	resp, err := client.ProcessPrices(context.Background(), &ProcessPricesRequest{TaskId: "pp"}, opts...)
	require.Nil(t, resp)
	require.ErrorIs(t, err, boom)
	require.Equal(t, TaskService_ProcessPrices_FullMethodName, conn.lastMethod)
	require.Len(t, conn.lastOpts, len(opts)+1)
}

func TestTaskServiceClientErrorBranches(t *testing.T) {
	testCases := []struct {
		name   string
		method string
		call   func(TaskServiceClient) error
	}{
		{
			name:   "CollectBinance",
			method: TaskService_CollectBinance_FullMethodName,
			call: func(client TaskServiceClient) error {
				_, err := client.CollectBinance(context.Background(), &CollectBinanceRequest{TaskId: "cb"})
				return err
			},
		},
		{
			name:   "CollectBinanceByDate",
			method: TaskService_CollectBinanceByDate_FullMethodName,
			call: func(client TaskServiceClient) error {
				_, err := client.CollectBinanceByDate(context.Background(), &CollectBinanceByDateRequest{TaskId: "cbd"})
				return err
			},
		},
		{
			name:   "CollectUniswap",
			method: TaskService_CollectUniswap_FullMethodName,
			call: func(client TaskServiceClient) error {
				_, err := client.CollectUniswap(context.Background(), &CollectUniswapRequest{TaskId: "cu"})
				return err
			},
		},
		{
			name:   "Analyse",
			method: TaskService_Analyse_FullMethodName,
			call: func(client TaskServiceClient) error {
				_, err := client.Analyse(context.Background(), &AnalyseRequest{TaskId: "an"})
				return err
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			expect := errors.New("call failed: " + tc.name)
			conn := &fakeConn{errors: map[string]error{tc.method: expect}}
			client := NewTaskServiceClient(conn)
			err := tc.call(client)
			require.ErrorIs(t, err, expect)
			require.Equal(t, tc.method, conn.lastMethod)
		})
	}
}

type noopServer struct {
	UnimplementedTaskServiceServer
}

func (n *noopServer) CollectBinance(ctx context.Context, req *CollectBinanceRequest) (*TaskResponse, error) {
	return &TaskResponse{TaskId: req.GetTaskId()}, nil
}

func TestRegisterTaskServiceServer(t *testing.T) {
	srv := grpc.NewServer()
	RegisterTaskServiceServer(srv, &noopServer{})
	srv.Stop()
}

func TestUnimplementedTaskServiceServerReturnsCodes(t *testing.T) {
	server := &UnimplementedTaskServiceServer{}
	ctx := context.Background()
	checks := []struct {
		name string
		run  func() error
	}{
		{"CollectBinance", func() error { _, err := server.CollectBinance(ctx, &CollectBinanceRequest{}); return err }},
		{"CollectBinanceByDate", func() error { _, err := server.CollectBinanceByDate(ctx, &CollectBinanceByDateRequest{}); return err }},
		{"CollectUniswap", func() error { _, err := server.CollectUniswap(ctx, &CollectUniswapRequest{}); return err }},
		{"ProcessPrices", func() error { _, err := server.ProcessPrices(ctx, &ProcessPricesRequest{}); return err }},
		{"Analyse", func() error { _, err := server.Analyse(ctx, &AnalyseRequest{}); return err }},
	}

	for _, tc := range checks {
		t.Run(tc.name, func(t *testing.T) {
			err := tc.run()
			require.Error(t, err)
			st, ok := status.FromError(err)
			require.True(t, ok)
			require.Equal(t, codes.Unimplemented, st.Code())
		})
	}
}

type spyTaskServer struct {
	UnimplementedTaskServiceServer
	lastMethod string
	lastReq    interface{}
}

func (s *spyTaskServer) CollectBinance(ctx context.Context, req *CollectBinanceRequest) (*TaskResponse, error) {
	s.lastMethod = "CollectBinance"
	s.lastReq = req
	return &TaskResponse{TaskId: req.GetTaskId()}, nil
}

func (s *spyTaskServer) CollectBinanceByDate(ctx context.Context, req *CollectBinanceByDateRequest) (*TaskResponse, error) {
	s.lastMethod = "CollectBinanceByDate"
	s.lastReq = req
	return &TaskResponse{TaskId: req.GetTaskId()}, nil
}

func (s *spyTaskServer) CollectUniswap(ctx context.Context, req *CollectUniswapRequest) (*TaskResponse, error) {
	s.lastMethod = "CollectUniswap"
	s.lastReq = req
	return &TaskResponse{TaskId: req.GetTaskId()}, nil
}

func (s *spyTaskServer) ProcessPrices(ctx context.Context, req *ProcessPricesRequest) (*TaskResponse, error) {
	s.lastMethod = "ProcessPrices"
	s.lastReq = req
	return &TaskResponse{TaskId: req.GetTaskId()}, nil
}

func (s *spyTaskServer) Analyse(ctx context.Context, req *AnalyseRequest) (*TaskResponse, error) {
	s.lastMethod = "Analyse"
	s.lastReq = req
	return &TaskResponse{TaskId: req.GetTaskId()}, nil
}

func TestCollectBinanceHandlerInvokesServer(t *testing.T) {
	rec := &spyTaskServer{}
	dec := func(v interface{}) error {
		req := v.(*CollectBinanceRequest)
		req.TaskId = "decoded"
		return nil
	}
	called := false
	interceptor := func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		called = true
		require.Equal(t, TaskService_CollectBinance_FullMethodName, info.FullMethod)
		return handler(ctx, req)
	}

	resp, err := _TaskService_CollectBinance_Handler(rec, context.Background(), dec, interceptor)
	require.NoError(t, err)
	require.True(t, called)
	require.NotNil(t, rec.lastReq)
	require.Equal(t, "decoded", rec.lastReq.(*CollectBinanceRequest).GetTaskId())
	msg, ok := resp.(*TaskResponse)
	require.True(t, ok)
	require.Equal(t, "decoded", msg.TaskId)
}

func TestTaskServiceHandlersWithoutInterceptor(t *testing.T) {
	srv := &spyTaskServer{}
	ctx := context.Background()
	testCases := []struct {
		name       string
		handler    func(interface{}, context.Context, func(interface{}) error, grpc.UnaryServerInterceptor) (interface{}, error)
		prep       func(interface{}) error
		wantMethod string
	}{
		{"CollectBinance", _TaskService_CollectBinance_Handler, func(v interface{}) error {
			req := v.(*CollectBinanceRequest)
			req.TaskId = "cb"
			return nil
		}, "CollectBinance"},
		{"CollectBinanceByDate", _TaskService_CollectBinanceByDate_Handler, func(v interface{}) error {
			req := v.(*CollectBinanceByDateRequest)
			req.TaskId = "cbd"
			return nil
		}, "CollectBinanceByDate"},
		{"CollectUniswap", _TaskService_CollectUniswap_Handler, func(v interface{}) error {
			req := v.(*CollectUniswapRequest)
			req.TaskId = "cu"
			return nil
		}, "CollectUniswap"},
		{"ProcessPrices", _TaskService_ProcessPrices_Handler, func(v interface{}) error {
			req := v.(*ProcessPricesRequest)
			req.TaskId = "pp"
			return nil
		}, "ProcessPrices"},
		{"Analyse", _TaskService_Analyse_Handler, func(v interface{}) error {
			req := v.(*AnalyseRequest)
			req.TaskId = "an"
			return nil
		}, "Analyse"},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			srv.lastMethod = ""
			srv.lastReq = nil
			resp, err := tc.handler(srv, ctx, tc.prep, nil)
			require.NoError(t, err)
			require.Equal(t, tc.wantMethod, srv.lastMethod)
			require.NotNil(t, srv.lastReq)
			msg, ok := resp.(*TaskResponse)
			require.True(t, ok)
			require.Equal(t, srv.lastReq.(interface{ GetTaskId() string }).GetTaskId(), msg.TaskId)
		})
	}
}

func TestTaskServiceHandlersWithInterceptor(t *testing.T) {
	srv := &spyTaskServer{}
	ctx := context.Background()
	testCases := []struct {
		name       string
		handler    func(interface{}, context.Context, func(interface{}) error, grpc.UnaryServerInterceptor) (interface{}, error)
		prep       func(interface{}) error
		fullMethod string
	}{
		{
			name:    "CollectBinanceByDate",
			handler: _TaskService_CollectBinanceByDate_Handler,
			prep: func(v interface{}) error {
				v.(*CollectBinanceByDateRequest).TaskId = "cbd"
				return nil
			},
			fullMethod: TaskService_CollectBinanceByDate_FullMethodName,
		},
		{
			name:    "CollectUniswap",
			handler: _TaskService_CollectUniswap_Handler,
			prep: func(v interface{}) error {
				v.(*CollectUniswapRequest).TaskId = "cu"
				return nil
			},
			fullMethod: TaskService_CollectUniswap_FullMethodName,
		},
		{
			name:    "ProcessPrices",
			handler: _TaskService_ProcessPrices_Handler,
			prep: func(v interface{}) error {
				v.(*ProcessPricesRequest).TaskId = "pp"
				return nil
			},
			fullMethod: TaskService_ProcessPrices_FullMethodName,
		},
		{
			name:    "Analyse",
			handler: _TaskService_Analyse_Handler,
			prep: func(v interface{}) error {
				v.(*AnalyseRequest).TaskId = "an"
				return nil
			},
			fullMethod: TaskService_Analyse_FullMethodName,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			called := false
			srv.lastMethod = ""
			srv.lastReq = nil
			resp, err := tc.handler(srv, ctx, tc.prep, func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
				called = true
				require.Equal(t, tc.fullMethod, info.FullMethod)
				require.Equal(t, srv, info.Server)
				return handler(ctx, req)
			})
			require.NoError(t, err)
			require.True(t, called)
			require.Equal(t, tc.name, srv.lastMethod)
			require.NotNil(t, resp)
		})
	}
}

func TestTaskServiceHandlerDecoderError(t *testing.T) {
	decErr := errors.New("boom")
	handlers := []struct {
		name    string
		handler func(interface{}, context.Context, func(interface{}) error, grpc.UnaryServerInterceptor) (interface{}, error)
	}{
		{"CollectBinance", _TaskService_CollectBinance_Handler},
		{"CollectBinanceByDate", _TaskService_CollectBinanceByDate_Handler},
		{"CollectUniswap", _TaskService_CollectUniswap_Handler},
		{"ProcessPrices", _TaskService_ProcessPrices_Handler},
		{"Analyse", _TaskService_Analyse_Handler},
	}

	for _, tc := range handlers {
		t.Run(tc.name, func(t *testing.T) {
			_, err := tc.handler(&spyTaskServer{}, context.Background(), func(interface{}) error {
				return decErr
			}, nil)
			require.ErrorIs(t, err, decErr)
		})
	}
}

func TestTaskServiceServiceDescMetadata(t *testing.T) {
	require.Equal(t, "task.proto", TaskService_ServiceDesc.Metadata)
	var names []string
	for _, m := range TaskService_ServiceDesc.Methods {
		names = append(names, m.MethodName)
	}
	require.ElementsMatch(t, []string{
		"CollectBinance",
		"CollectBinanceByDate",
		"CollectUniswap",
		"ProcessPrices",
		"Analyse",
	}, names)
}

func TestTaskStatusEnumHelpers(t *testing.T) {
	for value, name := range TaskStatus_name {
		t.Run(name, func(t *testing.T) {
			enum := TaskStatus(value)
			require.Equal(t, name, enum.String())
			require.Equal(t, protoreflect.EnumNumber(value), enum.Number())
			require.Equal(t, value, int32(TaskStatus_value[name]))
		})
	}

	enum := TaskStatus_RUNNING
	ptr := enum.Enum()
	require.NotNil(t, ptr)
	require.Equal(t, enum, *ptr)
	require.NotNil(t, enum.Descriptor())
	require.NotNil(t, enum.Type())
}

func TestTaskProtoMessagesRoundTrip(t *testing.T) {
	testCases := []struct {
		name string
		msg  proto.Message
	}{
		{"CollectBinanceRequest", &CollectBinanceRequest{TaskId: "cb", ImportPercentage: 70, ChunkSize: 5}},
		{"CollectBinanceByDateRequest", &CollectBinanceByDateRequest{TaskId: "cbd", StartTs: 1, EndTs: 2}},
		{"CollectUniswapRequest", &CollectUniswapRequest{TaskId: "cu", PoolAddress: "pool", StartTs: 3, EndTs: 4}},
		{"ProcessPricesRequest", &ProcessPricesRequest{
			TaskId:              "pp",
			StartDate:           1,
			EndDate:             2,
			AggregationInterval: "1m",
			Overwrite:           true,
			DbOverrides:         map[string]string{"dsn": "postgres"},
		}},
		{"AnalyseRequest", &AnalyseRequest{TaskId: "ar", BatchId: 9, Overwrite: true, StrategyJson: "{}"}},
		{"TaskResponse", &TaskResponse{TaskId: "tr", Status: TaskStatus_SUCCESS}},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			data, err := proto.Marshal(tc.msg)
			require.NoError(t, err)

			clone := proto.Clone(tc.msg)
			require.Equal(t, messageString(tc.msg), messageString(clone))
			require.True(t, proto.Equal(tc.msg, clone))
			require.NotNil(t, tc.msg.ProtoReflect().Descriptor())

			resetProtoMessage(tc.msg)
			_ = messageString(tc.msg)
			require.NotNil(t, tc.msg.ProtoReflect().Descriptor())

			newMsg := proto.Clone(tc.msg)
			require.NoError(t, proto.Unmarshal(data, newMsg))
			require.True(t, proto.Equal(clone, newMsg))
		})
	}
}

func TestTaskProtoNilGetters(t *testing.T) {
	var resp *TaskResponse
	require.Equal(t, "", resp.GetTaskId())
	require.Equal(t, TaskStatus_WAIT, resp.GetStatus())

	var analyse *AnalyseRequest
	require.Equal(t, "", analyse.GetTaskId())
	require.Equal(t, int32(0), analyse.GetBatchId())
}

func TestTaskProtoRawDescCaching(t *testing.T) {
	first := file_task_proto_rawDescGZIP()
	second := file_task_proto_rawDescGZIP()
	require.NotEmpty(t, first)
	require.Equal(t, first, second)
}

func TestTaskProtoGetterDefaultsAndValues(t *testing.T) {
	t.Run("CollectBinanceRequest", func(t *testing.T) {
		req := &CollectBinanceRequest{TaskId: "cb", ImportPercentage: 80, ChunkSize: 10}
		require.Equal(t, "cb", req.GetTaskId())
		require.Equal(t, int32(80), req.GetImportPercentage())
		require.Equal(t, int32(10), req.GetChunkSize())

		var nilReq *CollectBinanceRequest
		require.Equal(t, "", nilReq.GetTaskId())
		require.Equal(t, int32(0), nilReq.GetImportPercentage())
		require.Equal(t, int32(0), nilReq.GetChunkSize())
	})

	t.Run("CollectBinanceByDateRequest", func(t *testing.T) {
		req := &CollectBinanceByDateRequest{TaskId: "cbd", StartTs: 11, EndTs: 22}
		require.Equal(t, "cbd", req.GetTaskId())
		require.Equal(t, int32(11), req.GetStartTs())
		require.Equal(t, int32(22), req.GetEndTs())

		var nilReq *CollectBinanceByDateRequest
		require.Equal(t, "", nilReq.GetTaskId())
		require.Equal(t, int32(0), nilReq.GetStartTs())
		require.Equal(t, int32(0), nilReq.GetEndTs())
	})

	t.Run("CollectUniswapRequest", func(t *testing.T) {
		req := &CollectUniswapRequest{TaskId: "cu", PoolAddress: "pool", StartTs: 33, EndTs: 44}
		require.Equal(t, "cu", req.GetTaskId())
		require.Equal(t, "pool", req.GetPoolAddress())
		require.Equal(t, int32(33), req.GetStartTs())
		require.Equal(t, int32(44), req.GetEndTs())

		var nilReq *CollectUniswapRequest
		require.Equal(t, "", nilReq.GetTaskId())
		require.Equal(t, "", nilReq.GetPoolAddress())
		require.Equal(t, int32(0), nilReq.GetStartTs())
		require.Equal(t, int32(0), nilReq.GetEndTs())
	})

	t.Run("ProcessPricesRequest", func(t *testing.T) {
		req := &ProcessPricesRequest{
			TaskId:              "pp",
			StartDate:           1,
			EndDate:             2,
			AggregationInterval: "1m",
			Overwrite:           true,
			DbOverrides:         map[string]string{"dsn": "postgres"},
		}
		require.Equal(t, "pp", req.GetTaskId())
		require.Equal(t, int32(1), req.GetStartDate())
		require.Equal(t, int32(2), req.GetEndDate())
		require.Equal(t, "1m", req.GetAggregationInterval())
		require.True(t, req.GetOverwrite())
		require.Equal(t, "postgres", req.GetDbOverrides()["dsn"])

		var nilReq *ProcessPricesRequest
		require.Equal(t, "", nilReq.GetTaskId())
		require.Equal(t, int32(0), nilReq.GetStartDate())
		require.Equal(t, int32(0), nilReq.GetEndDate())
		require.Equal(t, "", nilReq.GetAggregationInterval())
		require.False(t, nilReq.GetOverwrite())
		require.Nil(t, nilReq.GetDbOverrides())
	})

	t.Run("AnalyseRequest", func(t *testing.T) {
		req := &AnalyseRequest{TaskId: "ar", BatchId: 9, Overwrite: true, StrategyJson: "{}"}
		require.Equal(t, "ar", req.GetTaskId())
		require.Equal(t, int32(9), req.GetBatchId())
		require.True(t, req.GetOverwrite())
		require.Equal(t, "{}", req.GetStrategyJson())

		var nilReq *AnalyseRequest
		require.Equal(t, "", nilReq.GetTaskId())
		require.Equal(t, int32(0), nilReq.GetBatchId())
		require.False(t, nilReq.GetOverwrite())
		require.Equal(t, "", nilReq.GetStrategyJson())
	})

	t.Run("TaskResponse", func(t *testing.T) {
		req := &TaskResponse{TaskId: "resp", Status: TaskStatus_SUCCESS}
		require.Equal(t, "resp", req.GetTaskId())
		require.Equal(t, TaskStatus_SUCCESS, req.GetStatus())

		var nilReq *TaskResponse
		require.Equal(t, "", nilReq.GetTaskId())
		require.Equal(t, TaskStatus_WAIT, nilReq.GetStatus())
	})
}

func TestTaskStatusDescriptors(t *testing.T) {
	data, idx := TaskStatus_RUNNING.EnumDescriptor()
	require.NotEmpty(t, data)
	require.Equal(t, []int{0}, idx)

	require.NotNil(t, File_task_proto)
	require.Contains(t, File_task_proto.Path(), "task.proto")
	require.GreaterOrEqual(t, File_task_proto.Messages().Len(), 6)
	require.Equal(t, protoreflect.FullName("task.v1.TaskStatus"), File_task_proto.Enums().Get(0).FullName())
}

func TestTaskProtoResetsAndReflection(t *testing.T) {
	exerciseProtoMessage(t, "CollectBinanceRequest",
		func() *CollectBinanceRequest {
			return &CollectBinanceRequest{TaskId: "cb", ImportPercentage: 88, ChunkSize: 7}
		},
		func() *CollectBinanceRequest { return &CollectBinanceRequest{} },
	)

	exerciseProtoMessage(t, "CollectBinanceByDateRequest",
		func() *CollectBinanceByDateRequest {
			return &CollectBinanceByDateRequest{TaskId: "cbd", StartTs: 11, EndTs: 22}
		},
		func() *CollectBinanceByDateRequest { return &CollectBinanceByDateRequest{} },
	)

	exerciseProtoMessage(t, "CollectUniswapRequest",
		func() *CollectUniswapRequest {
			return &CollectUniswapRequest{TaskId: "cu", PoolAddress: "pool", StartTs: 33, EndTs: 44}
		},
		func() *CollectUniswapRequest { return &CollectUniswapRequest{} },
	)

	exerciseProtoMessage(t, "ProcessPricesRequest",
		func() *ProcessPricesRequest {
			return &ProcessPricesRequest{
				TaskId:              "pp",
				StartDate:           1,
				EndDate:             2,
				AggregationInterval: "1m",
				Overwrite:           true,
				DbOverrides:         map[string]string{"dsn": "postgres"},
			}
		},
		func() *ProcessPricesRequest { return &ProcessPricesRequest{} },
	)

	exerciseProtoMessage(t, "AnalyseRequest",
		func() *AnalyseRequest {
			return &AnalyseRequest{TaskId: "ar", BatchId: 9, Overwrite: true, StrategyJson: "{}"}
		},
		func() *AnalyseRequest { return &AnalyseRequest{} },
	)

	exerciseProtoMessage(t, "TaskResponse",
		func() *TaskResponse {
			return &TaskResponse{TaskId: "resp", Status: TaskStatus_SUCCESS}
		},
		func() *TaskResponse { return &TaskResponse{} },
	)
}

type protoTestSubject interface {
	proto.Message
	interface {
		Reset()
		String() string
		Descriptor() ([]byte, []int)
		ProtoMessage()
	}
}

func exerciseProtoMessage[T protoTestSubject](t *testing.T, name string, populated func() T, zero func() T) {
	t.Helper()
	t.Run(name, func(t *testing.T) {
		msg := populated()
		zeroMsg := zero()
		require.NotEqual(t, zeroMsg.String(), msg.String())
		msg.Reset()
		require.True(t, proto.Equal(msg, zeroMsg))
		msg.ProtoMessage()
		require.NotNil(t, msg.ProtoReflect().Descriptor())
		_, idx := msg.Descriptor()
		require.NotEmpty(t, idx)
		var nilMsg T
		require.NotNil(t, nilMsg.ProtoReflect().Descriptor())
	})
}

func resetProtoMessage(m proto.Message) {
	switch v := m.(type) {
	case *CollectBinanceRequest:
		v.Reset()
	case *CollectBinanceByDateRequest:
		v.Reset()
	case *CollectUniswapRequest:
		v.Reset()
	case *ProcessPricesRequest:
		v.Reset()
	case *AnalyseRequest:
		v.Reset()
	case *TaskResponse:
		v.Reset()
	default:
		panic("unsupported proto message type")
	}
}

func messageString(m proto.Message) string {
	type stringer interface{ String() string }
	if s, ok := m.(stringer); ok {
		return s.String()
	}
	return ""
}
