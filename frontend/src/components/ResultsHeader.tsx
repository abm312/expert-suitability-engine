'use client';

import { Clock, Filter, Zap } from 'lucide-react';

interface ResultsHeaderProps {
  query: string;
  totalResults: number;
  filteredCount: number;
  processingTime: number;
  metricsUsed: string[];
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
}: ResultsHeaderProps) {
  return (
    <div className="mb-6 animate-fade-in">
      <h2 className="text-2xl font-bold mb-2">
        Results for <span className="gradient-text">"{query}"</span>
      </h2>
      
      <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400">
        <span className="flex items-center gap-1.5">
          <Zap className="w-4 h-4 text-ocean-400" />
          {filteredCount} experts found
          {totalResults !== filteredCount && (
            <span className="text-gray-600">
              (of {totalResults} in database)
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
  );
}

