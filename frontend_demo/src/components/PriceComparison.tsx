import { useState, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { Calendar, Loader2, AlertCircle, BarChart3 } from 'lucide-react';

type LoadingState = 'idle' | 'loading' | 'success' | 'error';
type Theme = 'light' | 'dark';

interface PriceComparisonProps {
  theme: Theme;
}

// Mock data generator
const generateMockData = (startDate: Date, endDate: Date) => {
  const data: { time: string; uniswap: number; binance: number }[] = [];
  const start = startDate.getTime();
  const end = endDate.getTime();
  const interval = 5 * 60 * 1000; // 5 minutes
  
  let uniswapPrice = 2000 + Math.random() * 100;
  let binancePrice = uniswapPrice + Math.random() * 10 - 5;
  
  for (let time = start; time <= end; time += interval) {
    uniswapPrice += (Math.random() - 0.5) * 20;
    binancePrice = uniswapPrice + (Math.random() - 0.5) * 8;
    
    data.push({
      time: new Date(time).toISOString(),
      uniswap: Math.max(1800, Math.min(2200, uniswapPrice)),
      binance: Math.max(1800, Math.min(2200, binancePrice)),
    });
  }
  
  return data;
};

export function PriceComparison({ theme }: PriceComparisonProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  
  const [startDate, setStartDate] = useState('2025-09-01');
  const [endDate, setEndDate] = useState('2025-09-07');
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [data, setData] = useState<{ time: string; uniswap: number; binance: number }[]>([]);

  useEffect(() => {
    if (chartRef.current && data.length > 0) {
      if (!chartInstance.current) {
        chartInstance.current = echarts.init(chartRef.current);
      }

      const isDark = theme === 'dark';
      const textColor = isDark ? '#e6edf3' : '#24292f';
      const secondaryTextColor = isDark ? '#7d8590' : '#57606a';
      const backgroundColor = isDark ? '#161b22' : 'white';
      const borderColor = isDark ? '#30363d' : '#d0d7de';
      const gridColor = isDark ? '#21262d' : '#eaeef2';

      const option: echarts.EChartsOption = {
        backgroundColor: 'transparent',
        title: {
          text: 'USDT/ETH Price Comparison',
          left: 'center',
          top: 10,
          textStyle: {
            fontSize: 16,
            fontWeight: 600,
            color: textColor,
          },
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: backgroundColor,
          borderColor: borderColor,
          borderWidth: 1,
          textStyle: {
            color: textColor,
          },
          axisPointer: {
            type: 'cross',
            lineStyle: {
              color: borderColor,
            },
          },
          formatter: (params: any) => {
            const date = new Date(params[0].value[0]).toLocaleString('en-US');
            let result = `<div style="font-size: 12px;">`;
            result += `<div style="color: ${secondaryTextColor}; margin-bottom: 4px;">${date}</div>`;
            params.forEach((param: any) => {
              const color = param.seriesName === 'Uniswap V3' ? '#58a6ff' : '#f78166';
              result += `<div style="color: ${color}; margin: 2px 0;">`;
              result += `${param.marker} ${param.seriesName}: $${param.value[1].toFixed(2)}`;
              result += `</div>`;
            });
            result += `</div>`;
            return result;
          },
        },
        legend: {
          data: ['Uniswap V3', 'Binance'],
          top: 40,
          textStyle: {
            color: secondaryTextColor,
          },
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '12%',
          top: 90,
          containLabel: true,
        },
        toolbox: {
          feature: {
            dataZoom: {
              yAxisIndex: 'none',
            },
            restore: {},
            saveAsImage: {},
          },
          iconStyle: {
            borderColor: secondaryTextColor,
          },
          emphasis: {
            iconStyle: {
              borderColor: '#58a6ff',
            },
          },
          right: 20,
          top: 40,
        },
        xAxis: {
          type: 'time',
          boundaryGap: false,
          axisLine: {
            lineStyle: {
              color: borderColor,
            },
          },
          axisLabel: {
            color: secondaryTextColor,
            fontSize: 11,
            formatter: (value: number) => {
              const date = new Date(value);
              return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
            },
          },
          splitLine: {
            lineStyle: {
              color: gridColor,
            },
          },
        },
        yAxis: {
          type: 'value',
          name: 'Price (USDT)',
          nameTextStyle: {
            color: secondaryTextColor,
            fontSize: 11,
          },
          axisLine: {
            lineStyle: {
              color: borderColor,
            },
          },
          axisLabel: {
            color: secondaryTextColor,
            fontSize: 11,
            formatter: '${value}',
          },
          splitLine: {
            lineStyle: {
              color: gridColor,
            },
          },
          scale: true,
        },
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: 100,
          },
          {
            start: 0,
            end: 100,
            backgroundColor: isDark ? '#0d1117' : '#f6f8fa',
            fillerColor: 'rgba(88, 166, 255, 0.1)',
            borderColor: borderColor,
            handleStyle: {
              color: '#58a6ff',
              borderColor: '#58a6ff',
            },
            textStyle: {
              color: secondaryTextColor,
            },
            dataBackground: {
              lineStyle: {
                color: borderColor,
              },
              areaStyle: {
                color: gridColor,
              },
            },
          },
        ],
        series: [
          {
            name: 'Uniswap V3',
            type: 'line',
            smooth: true,
            symbol: 'none',
            sampling: 'lttb',
            lineStyle: {
              width: 2,
              color: '#58a6ff',
            },
            itemStyle: {
              color: '#58a6ff',
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                {
                  offset: 0,
                  color: 'rgba(88, 166, 255, 0.3)',
                },
                {
                  offset: 1,
                  color: 'rgba(88, 166, 255, 0.05)',
                },
              ]),
            },
            data: data.map((d) => [d.time, d.uniswap]),
          },
          {
            name: 'Binance',
            type: 'line',
            smooth: true,
            symbol: 'none',
            sampling: 'lttb',
            lineStyle: {
              width: 2,
              color: '#f78166',
            },
            itemStyle: {
              color: '#f78166',
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                {
                  offset: 0,
                  color: 'rgba(247, 129, 102, 0.3)',
                },
                {
                  offset: 1,
                  color: 'rgba(247, 129, 102, 0.05)',
                },
              ]),
            },
            data: data.map((d) => [d.time, d.binance]),
          },
        ],
      };

      chartInstance.current.setOption(option);
    }

    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, [data, theme]);

  const handleLoad = async () => {
    setLoadingState('loading');
    
    await new Promise((resolve) => setTimeout(resolve, 1500));
    
    try {
      const mockData = generateMockData(new Date(startDate), new Date(endDate));
      setData(mockData);
      setLoadingState('success');
    } catch (error) {
      setLoadingState('error');
    }
  };

  const isDark = theme === 'dark';

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className={`rounded-md border p-4 ${
        isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'
      }`}>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
              Start Date
            </label>
            <div className="relative">
              <Calendar className={`absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 ${
                isDark ? 'text-[#7d8590]' : 'text-[#57606a]'
              }`} />
              <input
                type="date"
                value={startDate}
                min="2025-09-01"
                max="2025-09-30"
                onChange={(e) => setStartDate(e.target.value)}
                className={`w-full pl-9 pr-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark 
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]' 
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
            </div>
          </div>
          
          <div className="flex-1 min-w-[200px]">
            <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
              End Date
            </label>
            <div className="relative">
              <Calendar className={`absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 ${
                isDark ? 'text-[#7d8590]' : 'text-[#57606a]'
              }`} />
              <input
                type="date"
                value={endDate}
                min="2025-09-01"
                max="2025-09-30"
                onChange={(e) => setEndDate(e.target.value)}
                className={`w-full pl-9 pr-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark 
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]' 
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
            </div>
          </div>
          
          <button
            onClick={handleLoad}
            disabled={loadingState === 'loading'}
            className="px-4 py-1.5 bg-[#238636] text-white rounded-md text-sm hover:bg-[#2ea043] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loadingState === 'loading' && <Loader2 className="w-4 h-4 animate-spin" />}
            {loadingState === 'loading' ? 'Loading...' : 'Load Data'}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className={`rounded-md border p-4 ${
        isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'
      }`}>
        {loadingState === 'idle' && (
          <div className={`h-[500px] flex items-center justify-center ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
            <div className="text-center">
              <BarChart3 className="w-16 h-16 mx-auto mb-3 opacity-50" />
              <p className="text-sm">Select date range and click "Load Data"</p>
              <p className={`text-xs mt-1 ${isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'}`}>to view price chart</p>
            </div>
          </div>
        )}
        
        {loadingState === 'loading' && (
          <div className="h-[500px] flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-12 h-12 text-[#58a6ff] animate-spin mx-auto mb-3" />
              <p className="text-[#58a6ff] text-sm">Loading data...</p>
            </div>
          </div>
        )}
        
        {loadingState === 'error' && (
          <div className="h-[500px] flex items-center justify-center">
            <div className="text-center">
              <AlertCircle className="w-12 h-12 text-[#f85149] mx-auto mb-3" />
              <p className="text-[#f85149] text-sm">Failed to load data</p>
              <p className={`text-xs mt-1 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Please try again</p>
            </div>
          </div>
        )}
        
        {loadingState === 'success' && data.length === 0 && (
          <div className="h-[500px] flex items-center justify-center">
            <div className="text-center">
              <AlertCircle className="w-12 h-12 text-[#d29922] mx-auto mb-3" />
              <p className="text-[#d29922] text-sm">No data available</p>
              <p className={`text-xs mt-1 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>for selected time range</p>
            </div>
          </div>
        )}
        
        {loadingState === 'success' && data.length > 0 && (
          <div ref={chartRef} className="h-[500px]" />
        )}
      </div>

      {/* Info */}
      {loadingState === 'success' && data.length > 0 && (
        <div className={`border rounded-md p-3 ${
          isDark 
            ? 'bg-[#388bfd26] border-[#1f6feb]'
            : 'bg-[#ddf4ff] border-[#54aeff]'
        }`}>
          <div className="flex items-start gap-2">
            <div className="text-[#58a6ff] mt-0.5">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className={`text-sm ${isDark ? 'text-[#e6edf3]' : 'text-[#0969da]'}`}>
                Use mouse wheel or toolbar to zoom chart. Loaded <span className="text-[#58a6ff]">{data.length}</span> data points.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
