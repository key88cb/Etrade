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
	h := NewHandler()

	// 定义API路由组
	apiV1 := r.Group("/api/v1")
	{
		// 3. 将路由绑定到 Handler 的方法上
		apiV1.GET("/opportunities", h.GetOpportunities)
		apiV1.GET("/price-comparison", h.GetPriceComparisonData)
	}

	return r
}
