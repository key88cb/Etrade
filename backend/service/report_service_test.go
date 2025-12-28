package service

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"backend/models"
	"backend/testutil"

	"github.com/johnfercher/maroto/pkg/consts"
	"github.com/johnfercher/maroto/pkg/pdf"
	"github.com/stretchr/testify/require"
)

func TestReportServiceLifecycle(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	svc := NewReportService(db)
	ctx := context.Background()

	// seed data for DB-backed branch
	require.NoError(t, db.Create(&models.ArbitrageOpportunity{
		BatchID:      1,
		BuyPlatform:  "Binance",
		SellPlatform: "Uniswap",
		BuyPrice:     1000,
		SellPrice:    1015,
		ProfitUSDT:   15,
		CreatedAt:    time.Now(),
	}).Error)

	report, err := svc.CreateReport(ctx, 1, 2, "pdf", "")
	require.NoError(t, err)

	wd := t.TempDir()
	cwd, _ := os.Getwd()
	require.NoError(t, os.Chdir(wd))
	t.Cleanup(func() { _ = os.Chdir(cwd) })

	require.NoError(t, svc.GenerateReportFile(report.ID, 1, "pdf"))
	stored, err := svc.GetReport(ctx, report.ID)
	require.NoError(t, err)
	require.Equal(t, "SUCCESS", stored.Status)
	require.FileExists(t, stored.FilePath)

	reports, err := svc.ListReports(ctx, 1)
	require.NoError(t, err)
	require.Len(t, reports, 1)

	require.NoError(t, svc.DeleteReport(ctx, report.ID))
	reports, err = svc.ListReports(ctx, 1)
	require.NoError(t, err)
	require.Len(t, reports, 0)
}

func TestGenerateReportUsesMockData(t *testing.T) {
	db := testutil.NewInMemoryDB(t)
	svc := NewReportService(db)
	ctx := context.Background()

	report, err := svc.CreateReport(ctx, 99, 0, "pdf", "")
	require.NoError(t, err)

	wd := t.TempDir()
	cwd, _ := os.Getwd()
	require.NoError(t, os.Chdir(wd))
	defer func() { _ = os.Chdir(cwd) }()

	require.NoError(t, svc.GenerateReportFile(report.ID, 99, "pdf"))
	stored, err := svc.GetReport(ctx, report.ID)
	require.NoError(t, err)
	require.Equal(t, "SUCCESS", stored.Status)
}

func TestReportHelpers(t *testing.T) {
	require.Equal(t, "$1.23", safeFloat(1.23))
	require.Equal(t, "$1.23", safeFloat(float32(1.23)))
	require.Equal(t, "value", safeFloat("value"))

	data := (&ReportService{}).generateMockData(2)
	require.Len(t, data, 2)

	m := pdf.NewMaroto(consts.Portrait, consts.A4)
	(&ReportService{}).renderCard(m, "title", "value")

	gray := getGrayColor()
	require.EqualValues(t, 100, gray.Red)

	tmpDir := t.TempDir()
	db := testutil.NewInMemoryDB(t)
	svc := NewReportService(db)
	ctx := context.Background()
	report, err := svc.CreateReport(ctx, 1, 1, "pdf", "")
	require.NoError(t, err)
	cwd, _ := os.Getwd()
	require.NoError(t, os.Chdir(tmpDir))
	t.Cleanup(func() { _ = os.Chdir(cwd) })
	require.NoError(t, svc.updateStatus(report.ID, "SUCCESS", filepath.Join(tmpDir, "file.pdf")))
}
