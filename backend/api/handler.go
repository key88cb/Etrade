package api

import (
	"net/http"

	"backend/service"
	"backend/utils"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	service *service.Service
}

func NewHandler() *Handler {
	return &Handler{service: service.NewService()}
}

func (h *Handler) GetOpportunities(c *gin.Context) {
	opportunities, err := h.service.GetOpportunities()
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
	}
	utils.Success(c, opportunities)
}
