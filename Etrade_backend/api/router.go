// api/router.go
package api

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// SetupRouter 配置路由
func SetupRouter(db *gorm.DB) *gin.Engine {
	r := gin.Default()

	// 配置CORS中间件，允许所有来源的跨域请求 (在开发阶段)
	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	r.Use(cors.New(config))

	// 定义API路由组
	apiV1 := r.Group("/api/v1")
	{
		apiV1.GET("/opportunities", GetOpportunities(db))
		// 未来可以添加更多路由...
	}

	return r
}
