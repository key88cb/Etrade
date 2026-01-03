package api

import (
	"backend/utils"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

// AnalyzeOpportunity
// @Summary      使用 LLM 分析套利机会
// @Description  调用 LLM 对指定 ID 的套利机会进行风险分析
// @Tags         Opportunities
// @Accept       json
// @Produce      json
// @Param        id   path      int  true  "Opportunity ID"
// @Success      200  {object}  map[string]interface{}
// @Failure      400  {object}  api.ErrorResponse
// @Failure      500  {object}  api.ErrorResponse
// @Router       /opportunities/{id}/analyze [post]
func (h *Handler) AnalyzeOpportunity(c *gin.Context) {
	idStr := c.Param("id")
	id, err := strconv.ParseUint(idStr, 10, 64)
	if err != nil {
		utils.Fail(c, http.StatusBadRequest, "Invalid ID format")
		return
	}

	result, err := h.service.AnalyzeOpportunityWithLLM(uint(id))
	if err != nil {
		utils.Fail(c, http.StatusInternalServerError, err.Error())
		return
	}

	utils.Success(c, result)
}
