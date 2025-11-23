import { useState } from 'react';
import { PriceComparison } from './components/PriceComparison';
import { ArbitrageOpportunities } from './components/ArbitrageOpportunities';
import { DataManagement } from './components/DataManagement';
import { BarChart3, TrendingUp, Database, Activity, Sun, Moon } from 'lucide-react';

type TabType = 'comparison' | 'arbitrage' | 'management';
type Theme = 'light' | 'dark';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('comparison');
  const [theme, setTheme] = useState<Theme>('dark');

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]'}`}>
      <div className="relative">
        {/* Header */}
        <header className={theme === 'dark' ? 'bg-[#161b22] border-b border-[#30363d]' : 'bg-white border-b border-[#d0d7de]'}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-[#238636] rounded flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className={theme === 'dark' ? 'text-[#e6edf3]' : 'text-[#24292f]'}>Crypto Arbitrage System</h1>
                  <p className={`text-xs ${theme === 'dark' ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Analysis Platform v2.0</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={toggleTheme}
                  className={`p-2 rounded-md transition-colors ${
                    theme === 'dark' 
                      ? 'bg-[#21262d] border border-[#30363d] text-[#7d8590] hover:text-[#e6edf3] hover:border-[#58a6ff]'
                      : 'bg-[#f6f8fa] border border-[#d0d7de] text-[#57606a] hover:text-[#24292f] hover:border-[#0969da]'
                  }`}
                  title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                  {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                </button>
                
                <div className={`flex items-center gap-2 px-2.5 py-1 rounded-md ${
                  theme === 'dark' 
                    ? 'bg-[#238636]/10 border border-[#238636]/30'
                    : 'bg-[#dafbe1] border border-[#54a668]'
                }`}>
                  <div className="w-2 h-2 bg-[#3fb950] rounded-full" />
                  <span className={`text-xs ${theme === 'dark' ? 'text-[#3fb950]' : 'text-[#1a7f37]'}`}>Online</span>
                </div>
                <div className={`flex items-center gap-2 px-2.5 py-1 rounded-md ${
                  theme === 'dark'
                    ? 'bg-[#21262d] border border-[#30363d]'
                    : 'bg-[#f6f8fa] border border-[#d0d7de]'
                }`}>
                  <Activity className={`w-3.5 h-3.5 ${theme === 'dark' ? 'text-[#7d8590]' : 'text-[#57606a]'}`} />
                  <span className={`text-xs ${theme === 'dark' ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>{new Date().toLocaleTimeString('en-US')}</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className={theme === 'dark' ? 'bg-[#0d1117] border-b border-[#21262d]' : 'bg-[#f6f8fa] border-b border-[#d0d7de]'}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex gap-2">
              <button
                onClick={() => setActiveTab('comparison')}
                className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-colors text-sm ${
                  activeTab === 'comparison'
                    ? theme === 'dark'
                      ? 'border-[#f78166] text-[#e6edf3]'
                      : 'border-[#fd8c73] text-[#24292f]'
                    : theme === 'dark'
                      ? 'border-transparent text-[#7d8590] hover:text-[#e6edf3] hover:border-[#6e7681]'
                      : 'border-transparent text-[#57606a] hover:text-[#24292f] hover:border-[#d0d7de]'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                Price Comparison
              </button>
              <button
                onClick={() => setActiveTab('arbitrage')}
                className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-colors text-sm ${
                  activeTab === 'arbitrage'
                    ? theme === 'dark'
                      ? 'border-[#f78166] text-[#e6edf3]'
                      : 'border-[#fd8c73] text-[#24292f]'
                    : theme === 'dark'
                      ? 'border-transparent text-[#7d8590] hover:text-[#e6edf3] hover:border-[#6e7681]'
                      : 'border-transparent text-[#57606a] hover:text-[#24292f] hover:border-[#d0d7de]'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                Arbitrage Opportunities
              </button>
              <button
                onClick={() => setActiveTab('management')}
                className={`flex items-center gap-2 py-3 px-4 border-b-2 transition-colors text-sm ${
                  activeTab === 'management'
                    ? theme === 'dark'
                      ? 'border-[#f78166] text-[#e6edf3]'
                      : 'border-[#fd8c73] text-[#24292f]'
                    : theme === 'dark'
                      ? 'border-transparent text-[#7d8590] hover:text-[#e6edf3] hover:border-[#6e7681]'
                      : 'border-transparent text-[#57606a] hover:text-[#24292f] hover:border-[#d0d7de]'
                }`}
              >
                <Database className="w-4 h-4" />
                Data Management
              </button>
            </nav>
          </div>
        </div>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {activeTab === 'comparison' && <PriceComparison theme={theme} />}
          {activeTab === 'arbitrage' && <ArbitrageOpportunities theme={theme} />}
          {activeTab === 'management' && <DataManagement theme={theme} />}
        </main>
      </div>
    </div>
  );
}
