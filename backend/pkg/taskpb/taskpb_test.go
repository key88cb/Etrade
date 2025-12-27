package taskpb

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
)

type fakeConn struct {
	lastMethod string
}

func (f *fakeConn) Invoke(ctx context.Context, method string, args interface{}, reply interface{}, opts ...grpc.CallOption) error {
	f.lastMethod = method
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
