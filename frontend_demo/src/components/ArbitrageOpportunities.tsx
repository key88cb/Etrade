import { useState, useMemo } from 'react';
import { ArrowUpDown, TrendingUp, DollarSign, Activity, ChevronLeft, ChevronRight } from 'lucide-react';

type Theme = 'light' | 'dark';

interface ArbitrageOpportunitiesProps {
  theme: Theme;
}

interface ArbitrageOpportunity {
  id: string;
  timestamp: string;
  uniswapPrice: number;
  binancePrice: number;
  direction: 'DEX_TO_CEX' | 'CEX_TO_DEX';
  grossProfit: number;
  netProfit: number;
  gasUsdt: number;
  totalFees: number;
}

// Mock data - September 2025
const mockOpportunities: ArbitrageOpportunity[] = Array.from({ length: 47 }, (_, i) => {
  const direction = Math.random() > 0.5 ? 'DEX_TO_CEX' : 'CEX_TO_DEX';
  const uniswapPrice = 2000 + Math.random() * 100;
  const binancePrice = direction === 'DEX_TO_CEX' 
    ? uniswapPrice - (5 + Math.random() * 10)
    : uniswapPrice + (5 + Math.random() * 10);
  const grossProfit = Math.abs(binancePrice - uniswapPrice);
  const gasUsdt = 10 + Math.random() * 20;
  const totalFees = 2 + Math.random() * 3;
  const netProfit = grossProfit - gasUsdt - totalFees;
  
  const septemberStart = new Date('2025-09-01').getTime();
  const septemberEnd = new Date('2025-09-30').getTime();
  const randomTime = septemberStart + Math.random() * (septemberEnd - septemberStart);
  
  return {
    id: `ARB-${String(i + 1).padStart(4, '0')}`,
    timestamp: new Date(randomTime).toISOString(),
    uniswapPrice,
    binancePrice,
    direction,
    grossProfit,
    netProfit,
    gasUsdt,
    totalFees,
  };
}).filter(opp => opp.netProfit > 0.5);

type SortField = 'timestamp' | 'netProfit' | 'grossProfit';
type SortDirection = 'asc' | 'desc';

export function ArbitrageOpportunities({ theme }: ArbitrageOpportunitiesProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>('netProfit');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const itemsPerPage = 10;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedData = useMemo(() => {
    const sorted = [...mockOpportunities].sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return sortDirection === 'asc' 
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number);
    });
    return sorted;
  }, [sortField, sortDirection]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return sortedData.slice(start, start + itemsPerPage);
  }, [sortedData, currentPage]);

  const totalPages = Math.ceil(sortedData.length / itemsPerPage);

  const stats = useMemo(() => {
    const totalOpportunities = sortedData.length;
    const maxProfit = Math.max(...sortedData.map(o => o.netProfit));
    const avgProfit = sortedData.reduce((sum, o) => sum + o.netProfit, 0) / totalOpportunities;
    const totalPotentialProfit = sortedData.reduce((sum, o) => sum + o.netProfit, 0);
    
    return { totalOpportunities, maxProfit, avgProfit, totalPotentialProfit };
  }, [sortedData]);

  const isDark = theme === 'dark';

  return (
    <div className="space-y-4">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className={`rounded-md border p-4 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Total Opportunities</span>
            <Activity className="w-4 h-4 text-[#58a6ff]" />
          </div>
          <div className={`mb-1 ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>{stats.totalOpportunities}</div>
          <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>detected arbitrage chances</p>
        </div>

        <div className={`rounded-md border p-4 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Max Profit</span>
            <TrendingUp className="w-4 h-4 text-[#3fb950]" />
          </div>
          <div className={`mb-1 ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>${stats.maxProfit.toFixed(2)}</div>
          <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>highest net profit</p>
        </div>

        <div className={`rounded-md border p-4 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Average Profit</span>
            <DollarSign className="w-4 h-4 text-[#d29922]" />
          </div>
          <div className={`mb-1 ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>${stats.avgProfit.toFixed(2)}</div>
          <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>average net profit</p>
        </div>

        <div className={`rounded-md border p-4 ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>Total Potential</span>
            <TrendingUp className="w-4 h-4 text-[#bc8cff]" />
          </div>
          <div className={`mb-1 ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>${stats.totalPotentialProfit.toFixed(2)}</div>
          <p className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>cumulative profit</p>
        </div>
      </div>

      {/* Table */}
      <div className={`rounded-md border overflow-hidden ${isDark ? 'bg-[#161b22] border-[#30363d]' : 'bg-white border-[#d0d7de]'}`}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={isDark ? 'bg-[#0d1117]' : 'bg-[#f6f8fa]'}>
              <tr className={`border-b ${isDark ? 'border-[#30363d]' : 'border-[#d0d7de]'}`}>
                <th className={`px-4 py-3 text-left text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                  ID
                </th>
                <th 
                  className={`px-4 py-3 text-left text-xs cursor-pointer ${
                    isDark ? 'text-[#7d8590] hover:text-[#58a6ff]' : 'text-[#57606a] hover:text-[#0969da]'
                  }`}
                  onClick={() => handleSort('timestamp')}
                >
                  <div className="flex items-center gap-1">
                    Timestamp
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className={`px-4 py-3 text-left text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                  Direction
                </th>
                <th className={`px-4 py-3 text-right text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                  Uniswap
                </th>
                <th className={`px-4 py-3 text-right text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                  Binance
                </th>
                <th 
                  className={`px-4 py-3 text-right text-xs cursor-pointer ${
                    isDark ? 'text-[#7d8590] hover:text-[#58a6ff]' : 'text-[#57606a] hover:text-[#0969da]'
                  }`}
                  onClick={() => handleSort('grossProfit')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Gross
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className={`px-4 py-3 text-right text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                  Fees
                </th>
                <th 
                  className={`px-4 py-3 text-right text-xs cursor-pointer ${
                    isDark ? 'text-[#7d8590] hover:text-[#58a6ff]' : 'text-[#57606a] hover:text-[#0969da]'
                  }`}
                  onClick={() => handleSort('netProfit')}
                >
                  <div className="flex items-center justify-end gap-1">
                    Net Profit
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((opportunity) => (
                <tr key={opportunity.id} className={`border-b ${
                  isDark 
                    ? 'border-[#21262d] hover:bg-[#0d1117]' 
                    : 'border-[#d0d7de] hover:bg-[#f6f8fa]'
                }`}>
                  <td className={`px-4 py-3 text-sm ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>
                    {opportunity.id}
                  </td>
                  <td className={`px-4 py-3 text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                    {new Date(opportunity.timestamp).toLocaleString('en-US', { 
                      month: '2-digit', 
                      day: '2-digit', 
                      hour: '2-digit', 
                      minute: '2-digit',
                      second: '2-digit'
                    })}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                      opportunity.direction === 'DEX_TO_CEX'
                        ? isDark 
                          ? 'bg-[#388bfd26] text-[#58a6ff] border border-[#1f6feb]'
                          : 'bg-[#ddf4ff] text-[#0969da] border border-[#54aeff]'
                        : isDark
                          ? 'bg-[#6e40c926] text-[#bc8cff] border border-[#8957e5]'
                          : 'bg-[#fbefff] text-[#8250df] border border-[#d8b9ff]'
                    }`}>
                      {opportunity.direction === 'DEX_TO_CEX' ? '↓ DEX→CEX' : '↑ CEX→DEX'}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-sm text-right ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>
                    ${opportunity.uniswapPrice.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-sm text-right ${isDark ? 'text-[#e6edf3]' : 'text-[#24292f]'}`}>
                    ${opportunity.binancePrice.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-sm text-right ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                    ${opportunity.grossProfit.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-sm text-right ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
                    ${(opportunity.gasUsdt + opportunity.totalFees).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right">
                    <span className="text-[#3fb950]">
                      +${opportunity.netProfit.toFixed(2)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className={`px-4 py-3 border-t flex items-center justify-between ${
          isDark 
            ? 'border-[#30363d] bg-[#0d1117]' 
            : 'border-[#d0d7de] bg-[#f6f8fa]'
        }`}>
          <div className={`text-xs ${isDark ? 'text-[#7d8590]' : 'text-[#57606a]'}`}>
            Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, sortedData.length)} of {sortedData.length}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className={`p-1.5 border rounded text-sm transition-colors ${
                isDark
                  ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff] disabled:opacity-30 disabled:hover:text-[#7d8590] disabled:hover:border-[#30363d]'
                  : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da] disabled:opacity-30 disabled:hover:text-[#57606a] disabled:hover:border-[#d0d7de]'
              } disabled:cursor-not-allowed`}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`px-3 py-1 rounded text-sm ${
                    currentPage === pageNum
                      ? 'bg-[#1f6feb] text-white'
                      : isDark
                        ? 'border border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff]'
                        : 'border border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da]'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className={`p-1.5 border rounded text-sm transition-colors ${
                isDark
                  ? 'border-[#30363d] text-[#7d8590] hover:text-[#58a6ff] hover:border-[#58a6ff] disabled:opacity-30 disabled:hover:text-[#7d8590] disabled:hover:border-[#30363d]'
                  : 'border-[#d0d7de] text-[#57606a] hover:text-[#0969da] hover:border-[#0969da] disabled:opacity-30 disabled:hover:text-[#57606a] disabled:hover:border-[#d0d7de]'
              } disabled:cursor-not-allowed`}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
