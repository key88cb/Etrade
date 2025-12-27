package utils

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func newTestContext() (*gin.Context, *httptest.ResponseRecorder) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	return c, w
}

func TestSuccessWritesPayload(t *testing.T) {
	c, w := newTestContext()

	Success(c, gin.H{"foo": "bar"})

	require.Equal(t, http.StatusOK, w.Code)
	var resp Response
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	require.Equal(t, http.StatusOK, resp.Code)
	require.Equal(t, "成功", resp.Message)
}

func TestSuccessWithMessageOverridesDefault(t *testing.T) {
	c, w := newTestContext()

	SuccessWithMessage(c, "ok", gin.H{"foo": "bar"})

	require.Equal(t, http.StatusOK, w.Code)
	var resp Response
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	require.Equal(t, "ok", resp.Message)
}

func TestFailHelpers(t *testing.T) {
	t.Run("fail", func(t *testing.T) {
		c, w := newTestContext()
		Fail(c, http.StatusTeapot, "nope")

		require.Equal(t, http.StatusTeapot, w.Code)
		var resp Response
		require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
		require.Equal(t, "nope", resp.Message)
	})

	t.Run("bad request default", func(t *testing.T) {
		c, w := newTestContext()
		BadRequest(c, "")

		require.Equal(t, http.StatusBadRequest, w.Code)
		var resp Response
		require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
		require.Equal(t, "请求参数错误", resp.Message)
	})

	t.Run("server error custom", func(t *testing.T) {
		c, w := newTestContext()
		ServerError(c, "boom")

		require.Equal(t, http.StatusInternalServerError, w.Code)
		var resp Response
		require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
		require.Equal(t, "boom", resp.Message)
	})
}
