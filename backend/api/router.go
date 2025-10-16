// api/router.go
package api

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

// SetupRouter 配置路由
func SetupRouter() *gin.Engine {
	r := gin.Default()

	// 配置CORS中间件，允许所有来源的跨域请求 (在开发阶段)
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	r.Use(cors.New(config))

	// 初始化handler
	handler := NewHandler()

	// 定义API路由组
	apiV1 := r.Group("/api/v1")
	{
		apiV1.GET("/opportunities", handler.GetOpportunities)
		// 未来可以添加更多路由...
	}

	return r
}
