package service

import (
	"backend/models"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/spf13/viper"
	"gorm.io/datatypes"
)

type LLMRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type LLMResponse struct {
	Choices []Choice `json:"choices"`
}

type Choice struct {
	Message Message `json:"message"`
}

func (s *Service) AnalyzeOpportunityWithLLM(opportunityID uint) (datatypes.JSONMap, error) {
	// 1. 获取机会数据
	var opp models.ArbitrageOpportunity
	if err := s.db.First(&opp, opportunityID).Error; err != nil {
		return nil, err
	}

	// 2. 如果已有分析结果，直接返回 (可选：增加 force 参数强制刷新)
	if opp.LLMAnalysisJSON != nil {
		return opp.LLMAnalysisJSON, nil
	}

	// 3. 准备 LLM 请求配置
	apiKey := viper.GetString("llm.api_key")
	baseURL := viper.GetString("llm.base_url")
	model := viper.GetString("llm.model")

	if apiKey == "" {
		return nil, errors.New("LLM API Key is not configured")
	}

	// 4. 获取交易时间窗口及该窗口内的市场信息
	// 假设我们在 DetailsJSON 中存储了 block_time，如果没有则使用 CreatedAt
	// 窗口大小：前后 1 小时 (3600秒) 以获取足够的上下文
	tradeTime := opp.CreatedAt
	if val, ok := opp.DetailsJSON["block_time"]; ok {
		if tStr, ok := val.(string); ok {
			if t, err := time.Parse(time.RFC3339, tStr); err == nil {
				tradeTime = t
			}
		}
	}
	windowSeconds := int64(3600)
	startTime := tradeTime.UnixMilli() - windowSeconds*1000
	endTime := tradeTime.UnixMilli() + windowSeconds*1000

	marketData, _ := s.GetPriceComparisonData(startTime, endTime)

	// 5. 构造 Prompt
	contextData := map[string]interface{}{
		"buy_platform":  opp.BuyPlatform,
		"sell_platform": opp.SellPlatform,
		"buy_price":     opp.BuyPrice,
		"sell_price":    opp.SellPrice,
		"profit_usdt":   opp.ProfitUSDT,
		"risk_metrics":  opp.RiskMetricsJSON,
		"risk_metrics_definitions": map[string]string{
			"volatility":             "Price volatility in the current time window",
			"market_volume_eth":      "Total market volume (ETH)",
			"investment_usdt":        "Initial investment principal (USDT)",
			"estimated_slippage_pct": "Estimated slippage percentage based on Square Root Law",
			"risk_score":             "Profit quality score (0-100), higher is better. Score = (Net Profit / Gross Profit) * 100",
		},
		"market_context": map[string]interface{}{
			"window_start": time.UnixMilli(startTime).Format(time.RFC3339),
			"window_end":   time.UnixMilli(endTime).Format(time.RFC3339),
			"price_data":   marketData, // 包含 Uniswap 和 Binance 在该窗口内的价格序列
		},
		"timestamp": opp.CreatedAt.Format("2006-01-02 15:04:05"),
	}
	contextBytes, _ := json.Marshal(contextData)

	systemPrompt := `You are a senior crypto quantitative risk analyst. Your task is to evaluate a **Non-Atomic Arbitrage Opportunity** between Binance (CEX) and Uniswap (DEX).

**Input Data Structure:**
1. **Opportunity Details**: Core trade parameters including buy/sell platforms, prices, and projected profit (USDT).
2. **Risk Metrics**: Quantitative indicators pre-calculated by the system (e.g., Volatility, Slippage, Risk Score).
3. **Market Context**: Historical price data (+/- 1 hour) for both exchanges.

**Analysis Requirements:**
Assess the risk of this non-atomic arbitrage trade based on the provided data. Focus on price stability, execution risks (due to transfer delays), and the robustness of the net profit.

**Output Format (Strict JSON):**
You MUST return a valid JSON object. Do not wrap it in markdown code blocks.
{
  "risk_level": "High" | "Medium" | "Low",
  "summary": "Concise analysis (max 50 words) focusing on WHY this risk level was chosen.",
  "suggestions": [
    "Actionable advice 1 (e.g., Check liquidity depth on Uniswap)",
    "Actionable advice 2 (e.g., Wait for lower gas fees)",
    "Actionable advice 3"
  ],
  "warning": "Critical warning if applicable (e.g., 'Detected 5% price crash in 10s'), otherwise null or empty string."
}`

	userPrompt := fmt.Sprintf("Analyze this opportunity: %s", string(contextBytes))

	requestBody := LLMRequest{
		Model: model,
		Messages: []Message{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: userPrompt},
		},
	}
	jsonBody, _ := json.Marshal(requestBody)

	// 5. 发送请求
	req, err := http.NewRequest("POST", baseURL+"/chat/completions", bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("LLM API failed with status %d: %s", resp.StatusCode, string(bodyBytes))
	}

	// 6. 解析响应
	var llmResp LLMResponse
	if err := json.NewDecoder(resp.Body).Decode(&llmResp); err != nil {
		return nil, err
	}

	if len(llmResp.Choices) == 0 {
		return nil, errors.New("LLM returned no choices")
	}

	content := llmResp.Choices[0].Message.Content

	// 尝试提取 JSON (LLM 可能返回 Markdown 代码块)
	// 这里做一个简单的处理，假设 LLM 听话返回了纯 JSON
	// 如果包含 ```json ... ``` 需要 strip
	// 简单处理：直接尝试解析，失败则封装为文本
	var resultJSON datatypes.JSONMap
	if err := json.Unmarshal([]byte(content), &resultJSON); err != nil {
		// 尝试清理 markdown 标记
		// 这是一个简单的 fallback
		resultJSON = datatypes.JSONMap{
			"raw_analysis": content,
			"risk_level":   "Unknown",
		}
	}

	// 7. 保存结果到数据库
	opp.LLMAnalysisJSON = resultJSON
	if err := s.db.Save(&opp).Error; err != nil {
		return nil, err
	}

	return resultJSON, nil
}
