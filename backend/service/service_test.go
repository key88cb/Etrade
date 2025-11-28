package service

import (
	"testing"
	"time"

	"backend/models"
	"backend/testutil"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGetOpportunitiesSupportsPaginationAndOrdering(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	svc := NewService(db)

	seed := []models.ArbitrageOpportunity{
		{ID: 1, BatchID: 10, BuyPlatform: "Binance", SellPlatform: "Uniswap", ProfitUSDT: 50},
		{ID: 2, BatchID: 10, BuyPlatform: "Uniswap", SellPlatform: "Binance", ProfitUSDT: 75},
		{ID: 3, BatchID: 10, BuyPlatform: "Binance", SellPlatform: "Binance", ProfitUSDT: 20},
	}
	require.NoError(t, db.Create(&seed).Error)

	ops, pagination, err := svc.GetOpportunities(1, 2, "profit_usdt", "desc")
	require.NoError(t, err)
	require.NotNil(t, pagination)

	assert.Equal(t, int64(3), pagination.Total)
	assert.Equal(t, 1, pagination.Page)
	assert.Equal(t, 2, pagination.Limit)
	require.Len(t, ops, 2)
	assert.Equal(t, uint(2), ops[0].ID)
	assert.Equal(t, uint(1), ops[1].ID)

	opsPage2, _, err := svc.GetOpportunities(2, 2, "profit_usdt", "desc")
	require.NoError(t, err)
	require.Len(t, opsPage2, 1)
	assert.Equal(t, uint(3), opsPage2[0].ID)
}

func TestGetPriceComparisonDataFiltersWindowAndGroupsBySource(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	svc := NewService(db)

	base := time.Unix(1_700_000_000, 0).UTC()

	rows := []models.AggregatedPrice{
		{TimeBucket: base.Add(10 * time.Minute), Source: "Binance", AveragePrice: 3000},
		{TimeBucket: base.Add(20 * time.Minute), Source: "Uniswap", AveragePrice: 3050},
		{TimeBucket: base.Add(3 * time.Hour), Source: "Binance", AveragePrice: 2900},
	}
	require.NoError(t, db.Create(&rows).Error)

	start := base.Add(5 * time.Minute).UnixMilli()
	end := base.Add(30 * time.Minute).UnixMilli()

	data, err := svc.GetPriceComparisonData(start, end)
	require.NoError(t, err)

	require.Len(t, data["binance"], 1)
	require.Len(t, data["uniswap"], 1)

	assert.Equal(t, rows[0].AveragePrice, data["binance"][0][1])
	assert.Equal(t, rows[1].AveragePrice, data["uniswap"][0][1])

	// Ensure timestamps are expressed in milliseconds
	assert.Equal(t, rows[0].TimeBucket.UnixMilli(), data["binance"][0][0])
	assert.Equal(t, rows[1].TimeBucket.UnixMilli(), data["uniswap"][0][0])
}
