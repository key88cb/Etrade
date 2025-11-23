import { useState } from 'react';
import { Download, Database, TrendingUp, Play, CheckCircle2, Loader2, AlertCircle, Terminal } from 'lucide-react';

type TaskStatus = 'idle' | 'running' | 'success' | 'error';
type Theme = 'light' | 'dark';

interface DataManagementProps {
  theme: Theme;
}

interface Task {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  status: TaskStatus;
  lastRun?: string;
  duration?: string;
}

export function DataManagement({ theme }: DataManagementProps) {
  const [tasks, setTasks] = useState<Task[]>([
    {
      id: 'uniswap-ingest',
      name: 'Uniswap Data Ingestion',
      description: 'Fetch Uniswap V3 swap data via The Graph API',
      icon: <Download className="w-4 h-4" />,
      status: 'idle',
    },
    {
      id: 'binance-ingest',
      name: 'Binance Data Import',
      description: 'Import Binance historical trades from CSV',
      icon: <Download className="w-4 h-4" />,
      status: 'idle',
    },
    {
      id: 'aggregate',
      name: 'Data Aggregation',
      description: 'Aggregate raw data by time intervals',
      icon: <Database className="w-4 h-4" />,
      status: 'idle',
    },
    {
      id: 'analyze',
      name: 'Arbitrage Analysis',
      description: 'Detect arbitrage opportunities and calculate profits',
      icon: <TrendingUp className="w-4 h-4" />,
      status: 'idle',
    },
  ]);

  const [config, setConfig] = useState({
    startTimestamp: '1725148800', // 2025-09-01
    endTimestamp: '1727740800',   // 2025-09-30
    poolAddress: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640',
    csvPath: '/data/binance_aggTrades_ETHUSDT.csv',
    aggregationInterval: '5m',
    timeDelay: '15',
    profitThreshold: '0.5',
  });

  const runTask = async (taskId: string) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId ? { ...task, status: 'running' as TaskStatus } : task
    ));

    await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 2000));

    const success = Math.random() > 0.1;
    
    setTasks(prev => prev.map(task => 
      task.id === taskId ? {
        ...task,
        status: success ? 'success' as TaskStatus : 'error' as TaskStatus,
        lastRun: new Date().toLocaleString('en-US'),
        duration: `${(2 + Math.random() * 3).toFixed(1)}s`,
      } : task
    ));
  };

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-4 h-4 text-[#58a6ff] animate-spin" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-[#3fb950]" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-[#f85149]" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: TaskStatus) => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'success':
        return 'Success';
      case 'error':
        return 'Error';
      default:
        return 'Ready';
    }
  };

  const isDark = theme === 'dark';

  return (
    <div className="space-y-4">
      {/* Configuration Panel */}
      <div className={`rounded-md border p-4 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
        <div className="flex items-center gap-2 mb-4">
          <Terminal className={`w-4 h-4 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`} />
          <h2 className={isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}>Configuration Parameters</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Data Ingestion Config */}
          <div className="space-y-3">
            <h3 className={`text-xs mb-3 pb-2 border-b ${
              isDark ? 'text-[#7d8590] border-[#21262d]' : 'text-[#57606a] border-[#d0d7de]'
            }`}>Data Ingestion</h3>
            
            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                Start Timestamp (Unix seconds)
              </label>
              <input
                type="text"
                value={config.startTimestamp}
                onChange={(e) => setConfig({ ...config, startTimestamp: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
              <p className={`text-xs mt-1 ${isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'}`}>2025-09-01 00:00:00</p>
            </div>

            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                End Timestamp (Unix seconds)
              </label>
              <input
                type="text"
                value={config.endTimestamp}
                onChange={(e) => setConfig({ ...config, endTimestamp: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
              <p className={`text-xs mt-1 ${isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'}`}>2025-09-30 23:59:59</p>
            </div>

            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                Pool Address
              </label>
              <input
                type="text"
                value={config.poolAddress}
                onChange={(e) => setConfig({ ...config, poolAddress: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-xs font-mono ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
              <p className={`text-xs mt-1 ${isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'}`}>Uniswap V3 USDT/ETH Pool</p>
            </div>

            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                CSV Path
              </label>
              <input
                type="text"
                value={config.csvPath}
                onChange={(e) => setConfig({ ...config, csvPath: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
            </div>
          </div>

          {/* Analysis Config */}
          <div className="space-y-3">
            <h3 className={`text-xs mb-3 pb-2 border-b ${
              isDark ? 'text-[#7d8590] border-[#21262d]' : 'text-[#57606a] border-[#d0d7de]'
            }`}>Analysis Parameters</h3>
            
            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                Aggregation Interval
              </label>
              <select
                value={config.aggregationInterval}
                onChange={(e) => setConfig({ ...config, aggregationInterval: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              >
                <option value="1m">1 Minute</option>
                <option value="5m">5 Minutes</option>
                <option value="15m">15 Minutes</option>
                <option value="1h">1 Hour</option>
              </select>
            </div>

            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                Time Delay (seconds)
              </label>
              <input
                type="number"
                value={config.timeDelay}
                onChange={(e) => setConfig({ ...config, timeDelay: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
              <p className={`text-xs mt-1 ${isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'}`}>DEX to CEX price match delay</p>
            </div>

            <div>
              <label className={`block text-xs mb-1.5 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                Profit Threshold (USDT)
              </label>
              <input
                type="number"
                step="0.1"
                value={config.profitThreshold}
                onChange={(e) => setConfig({ ...config, profitThreshold: e.target.value })}
                className={`w-full px-3 py-1.5 border rounded-md focus:outline-none focus:ring-2 text-sm ${
                  isDark
                    ? 'bg-[#0d1117] border-[#30363d] text-[#e6edf3] focus:ring-[#1f6feb]'
                    : 'bg-[#f6f8fa] border-[#d0d7de] text-[#24292f] focus:ring-[#0969da]'
                } focus:border-transparent`}
              />
              <p className={`text-xs mt-1 ${isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'}`}>Minimum net profit to record</p>
            </div>

            <div className={`border rounded-md p-3 mt-3 ${
              isDark 
                ? 'bg-[#d2992214] border-[#9e6a03]'
                : 'bg-[#fff8c5] border-[#d4a72c]'
            }`}>
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-[#d29922] mt-0.5 flex-shrink-0" />
                <p className={`text-xs ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>
                  Recommended: Execute tasks in sequence (INGEST → AGGREGATE → ANALYZE)
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Task Execution Panel */}
      <div className={`rounded-md border p-4 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
        <div className="flex items-center gap-2 mb-4">
          <Play className={`w-4 h-4 ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`} />
          <h2 className={isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}>Task Execution</h2>
        </div>
        
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.id}
              className={`border rounded-md p-3 transition-colors ${
                isDark
                  ? 'border-[#30363d] hover:border-[#58a6ff] bg-[#0d1117]'
                  : 'border-[#d0d7de] hover:border-[#0969da] bg-[#f6f8fa]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <div className={`w-10 h-10 rounded flex items-center justify-center ${
                    task.status === 'success' ? isDark ? 'bg-[#26a64126] text-[#3fb950]' : 'bg-[#dafbe1] text-[#1a7f37]' :
                    task.status === 'error' ? isDark ? 'bg-[#f8514926] text-[#f85149]' : 'bg-[#ffebe9] text-[#cf222e]' :
                    task.status === 'running' ? isDark ? 'bg-[#388bfd26] text-[#58a6ff]' : 'bg-[#ddf4ff] text-[#0969da]' :
                    isDark ? 'bg-[#21262d] text-[#7d8590]' : 'bg-[#eaeef2] text-[#57606a]'
                  }`}>
                    {task.icon}
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className={`text-sm ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>{task.name}</h3>
                      {getStatusIcon(task.status)}
                    </div>
                    <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>{task.description}</p>
                    
                    {task.lastRun && (
                      <div className={`flex items-center gap-3 mt-1.5 text-xs ${
                        isDark ? 'text-[#6e7681]' : 'text-[#6e7781]'
                      }`}>
                        <span>Last run: {task.lastRun}</span>
                        {task.duration && <span>Duration: {task.duration}</span>}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-1 rounded ${
                    task.status === 'success' ? isDark ? 'bg-[#26a64126] text-[#3fb950] border border-[#3fb950]' : 'bg-[#dafbe1] text-[#1a7f37] border border-[#1f7f37]' :
                    task.status === 'error' ? isDark ? 'bg-[#f8514926] text-[#f85149] border border-[#f85149]' : 'bg-[#ffebe9] text-[#cf222e] border border-[#cf222e]' :
                    task.status === 'running' ? isDark ? 'bg-[#388bfd26] text-[#58a6ff] border border-[#58a6ff]' : 'bg-[#ddf4ff] text-[#0969da] border border-[#0969da]' :
                    isDark ? 'bg-[#21262d] text-[#7d8590] border border-[#30363d]' : 'bg-[#f6f8fa] text-[#57606a] border border-[#d0d7de]'
                  }`}>
                    {getStatusText(task.status)}
                  </span>
                  
                  <button
                    onClick={() => runTask(task.id)}
                    disabled={task.status === 'running'}
                    className="px-3 py-1.5 bg-[#238636] text-white rounded text-sm hover:bg-[#2ea043] transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5"
                  >
                    <Play className="w-3 h-3" />
                    Run
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className={`rounded-md border p-3 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded flex items-center justify-center ${
              isDark ? 'bg-[#26a64126]' : 'bg-[#dafbe1]'
            }`}>
              <CheckCircle2 className="w-5 h-5 text-[#3fb950]" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Database Status</p>
              <p className={isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}>Connected</p>
            </div>
          </div>
        </div>

        <div className={`rounded-md border p-3 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded flex items-center justify-center ${
              isDark ? 'bg-[#388bfd26]' : 'bg-[#ddf4ff]'
            }`}>
              <Database className="w-5 h-5 text-[#58a6ff]" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Raw Records</p>
              <p className={isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}>12,547</p>
            </div>
          </div>
        </div>

        <div className={`rounded-md border p-3 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded flex items-center justify-center ${
              isDark ? 'bg-[#6e40c926]' : 'bg-[#fbefff]'
            }`}>
              <TrendingUp className="w-5 h-5 text-[#bc8cff]" />
            </div>
            <div>
              <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Opportunities</p>
              <p className={isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}>47</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
