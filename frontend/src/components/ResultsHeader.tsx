'use client';

import { Clock, Download, Filter, Zap } from 'lucide-react';

interface ResultsHeaderProps {
  query: string;
  totalResults: number;
  filteredCount: number;
  processingTime: number;
  metricsUsed: string[];
  onExportCsv?: () => void;
  isExportingCsv?: boolean;
}

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else if (totalSeconds > 0) {
    return `${seconds}s`;
  } else {
    return `${ms.toFixed(0)}ms`;
  }
}

export function ResultsHeader({
  query,
  totalResults,
  filteredCount,
  processingTime,
  metricsUsed,
  onExportCsv,
  isExportingCsv = false,
}: ResultsHeaderProps) {
  return (
    <div className="mb-6 animate-fade-in">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-2xl font-bold mb-2">
            Results for <span className="gradient-text">"{query}"</span>
          </h2>
          
          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
            <span className="flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-ocean-400" />
              {filteredCount} experts found
              {totalResults !== filteredCount && (
                <span className="text-gray-600">
                  (of {totalResults} candidates)
                </span>
              )}
            </span>
            
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              {formatTime(processingTime)}
            </span>
            
            <span className="flex items-center gap-1.5">
              <Filter className="w-4 h-4" />
              {metricsUsed.length} metrics used
            </span>
          </div>
        </div>

        {onExportCsv && (
          <button
            type="button"
            onClick={onExportCsv}
            disabled={isExportingCsv}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-ocean-500/30 bg-ocean-500/10 px-4 py-2.5 text-sm font-medium text-ocean-200 transition-all hover:bg-ocean-500/20 hover:border-ocean-500/50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Download className="w-4 h-4" />
            <span>{isExportingCsv ? 'Exporting CSV...' : 'Export AI Creators CSV'}</span>
          </button>
        )}
      </div>
      
      {onExportCsv && (
        <p className="mt-3 text-xs text-gray-500">
          Downloads a curated CSV built from preset AI creator queries with stronger filters for editorial review.
        </p>
      )}
    </div>
  );
}
