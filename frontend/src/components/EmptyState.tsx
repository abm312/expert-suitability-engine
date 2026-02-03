'use client';

import { Search, Users, Plus, AlertTriangle, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  type: 'no-search' | 'no-results' | 'error';
  query?: string;
  errorMessage?: string;
  onDiscover?: () => void;
  onRetry?: () => void;
}

export function EmptyState({ type, query, errorMessage, onDiscover, onRetry }: EmptyStateProps) {
  if (type === 'no-search') {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
        <div className="w-20 h-20 rounded-full bg-ocean-500/10 flex items-center justify-center mb-6">
          <Search className="w-10 h-10 text-ocean-400" />
        </div>
        <h3 className="text-xl font-semibold text-gray-200 mb-2">Find Your Expert</h3>
        <p className="text-gray-400 text-center max-w-md">
          Describe the expertise you're looking for, and we'll find and rank the best
          YouTube creators who match your criteria.
        </p>
      </div>
    );
  }

  if (type === 'no-results') {
    return (
      <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
        <div className="w-20 h-20 rounded-full bg-flame-500/10 flex items-center justify-center mb-6">
          <Users className="w-10 h-10 text-flame-400" />
        </div>
        <h3 className="text-xl font-semibold text-gray-200 mb-2">No Experts Found</h3>
        <p className="text-gray-400 text-center max-w-md mb-6">
          {query 
            ? `We couldn't find any creators matching "${query}" with your current filters.`
            : "No creators in the database yet. Discover some to get started!"
          }
        </p>
        {onDiscover && (
          <button
            onClick={onDiscover}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Discover Creators
          </button>
        )}
        <p className="text-gray-500 text-sm mt-4">
          Try adjusting your filters or using different keywords.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
      <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center mb-6">
        <AlertTriangle className="w-10 h-10 text-red-400" />
      </div>
      <h3 className="text-xl font-semibold text-gray-200 mb-2">Something went wrong</h3>
      <p className="text-gray-400 text-center max-w-md mb-4">
        We encountered an error while searching.
      </p>
      {errorMessage && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 max-w-md mb-6">
          <p className="text-red-300 text-sm font-mono break-all">{errorMessage}</p>
        </div>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </button>
      )}
      <p className="text-gray-500 text-sm mt-4">
        Check that the backend server is running on port 8000
      </p>
    </div>
  );
}

