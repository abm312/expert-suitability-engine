'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { 
  SearchBar, 
  MetricControls, 
  FilterPanel, 
  CreatorCard, 
  ResultsHeader,
  EmptyState 
} from '@/components';
import { 
  SearchRequest, 
  SearchResponse, 
  MetricType, 
  MetricConfig, 
  FilterConfig,
  DEFAULT_METRICS 
} from '@/types';
import { api } from '@/lib/api';
import { Search, Github, Zap, Youtube, Database, Brain, CheckCircle, TrendingUp } from 'lucide-react';

const PROGRESS_STEPS = {
  embedding: { icon: Brain, label: 'Understanding your search', color: 'text-purple-400' },
  youtube: { icon: Youtube, label: 'Finding creators on YouTube', color: 'text-red-400' },
  populating: { icon: Database, label: 'Adding new creators to database', color: 'text-blue-400' },
  filtering: { icon: Zap, label: 'Applying your filters', color: 'text-orange-400' },
  scoring: { icon: TrendingUp, label: 'Ranking by expertise match', color: 'text-yellow-400' },
  done: { icon: CheckCircle, label: 'Done!', color: 'text-emerald-400' },
};

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [progress, setProgress] = useState<{ step: string; details: string }>({ step: '', details: '' });
  const progressInterval = useRef<NodeJS.Timeout | null>(null);
  
  // Search configuration
  const [metrics, setMetrics] = useState<Record<MetricType, MetricConfig>>(DEFAULT_METRICS);
  const [filters, setFilters] = useState<FilterConfig>({});

  // Poll for progress while loading
  useEffect(() => {
    if (isLoading) {
      progressInterval.current = setInterval(async () => {
        try {
          const prog = await api.getProgress();
          setProgress({ step: prog.step, details: prog.details });
        } catch (e) {
          // Ignore progress errors
        }
      }, 500);
    } else {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
        progressInterval.current = null;
      }
    }
    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, [isLoading]);

  const handleSearch = useCallback(async (query: string, keywords: string[]) => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    setProgress({ step: 'embedding', details: 'Starting search...' });

    const request: SearchRequest = {
      topic_query: query,
      topic_keywords: keywords,
      metrics,
      filters,
      limit: 10, // Show top 10 results only
      offset: 0,
    };

    try {
      const response = await api.searchCreators(request);
      setResults(response);
    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults(null);
    } finally {
      setIsLoading(false);
      setProgress({ step: '', details: '' });
    }
  }, [metrics, filters]);

  const handleReset = useCallback(() => {
    setHasSearched(false);
    setResults(null);
    setError(null);
    setIsLoading(false);
    setProgress({ step: '', details: '' });
  }, []);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-white/5 backdrop-blur-xl bg-slate-900/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleReset}
              className="flex items-center gap-3 hover:opacity-80 transition-opacity cursor-pointer"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ocean-500 to-ocean-600 flex items-center justify-center shadow-lg shadow-ocean-500/30">
                <Search className="w-5 h-5 text-white" />
              </div>
              <div className="text-left">
                <h1 className="font-bold text-lg tracking-tight">Expert Suitability Engine</h1>
                <p className="text-xs text-gray-500">YouTube Expert Discovery</p>
              </div>
            </button>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-gray-400 hover:text-gray-200 transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Landing Page Hero */}
        {!hasSearched && (
          <div className="text-center mb-16 animate-fade-in max-w-4xl mx-auto">
            <div className="mb-8 inline-flex items-center gap-2 px-4 py-2 bg-ocean-500/10 border border-ocean-500/20 rounded-full text-ocean-400 text-sm font-medium">
              <Search className="w-4 h-4" />
              Intelligent Expert Discovery
            </div>

            <h2 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
              Find the <span className="gradient-text">Perfect Expert</span>
              <br />for Your Project
            </h2>

            <p className="text-gray-400 text-xl mb-8 max-w-2xl mx-auto leading-relaxed">
              Multi-dimensional weighted scoring algorithm for expert network consulting.
              Semantic embeddings, quantitative metrics, and real-time data analysis to identify optimal subject matter experts.
            </p>

            {/* Simple feature highlights */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12 mb-8">
              <div className="glass-card p-6 text-left">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-4">
                  <Database className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold mb-2">5-Metric Composite Algorithm</h3>
                <p className="text-gray-400 text-sm">Normalized weighted scoring across credibility, topic authority, communication quality, temporal freshness, and growth trajectory</p>
              </div>

              <div className="glass-card p-6 text-left">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center mb-4">
                  <Youtube className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold mb-2">YouTube Data API Integration</h3>
                <p className="text-gray-400 text-sm">Quantitative analysis of channel statistics, content embeddings, transcript NLP, and engagement metrics via YouTube Data API v3</p>
              </div>

              <div className="glass-card p-6 text-left">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center mb-4">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Vector-Based Rankings</h3>
                <p className="text-gray-400 text-sm">Cosine similarity matching with dynamic weight normalization produces ranked results with explainable score breakdowns</p>
              </div>
            </div>
          </div>
        )}

        {/* Search section */}
        <div className="mb-8">
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        </div>

        {/* Controls & Results */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar controls */}
          <aside className="lg:w-80 flex-shrink-0 space-y-4">
            <MetricControls metrics={metrics} onChange={setMetrics} />
            <FilterPanel filters={filters} onChange={setFilters} />
            
            {/* Stats card */}
            {results && (
              <div className="glass-card p-5 animate-fade-in">
                <div className="flex items-center gap-3 mb-4">
                  <Zap className="w-5 h-5 text-flame-400" />
                  <span className="font-medium text-gray-200">Quick Stats</span>
                </div>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total in Database</span>
                    <span className="text-gray-200 font-mono">{results.total_results}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Matched Filters</span>
                    <span className="text-gray-200 font-mono">{results.filtered_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Search Time</span>
                    <span className="text-gray-200 font-mono">
                      {results.processing_time_ms >= 60000 
                        ? `${Math.floor(results.processing_time_ms / 60000)}m ${Math.floor((results.processing_time_ms % 60000) / 1000)}s`
                        : results.processing_time_ms >= 1000
                        ? `${Math.floor(results.processing_time_ms / 1000)}s`
                        : `${results.processing_time_ms.toFixed(0)}ms`
                      }
                    </span>
                  </div>
                </div>
              </div>
            )}
          </aside>

          {/* Results */}
          <div className="flex-1 min-w-0">
            {!hasSearched && (
              <EmptyState type="no-search" />
            )}

            {hasSearched && isLoading && (
              <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
                {/* Progress indicator */}
                <div className="glass-card p-8 max-w-md w-full">
                  <div className="flex items-center justify-center mb-6">
                    <div className="w-16 h-16 border-4 border-ocean-500/30 border-t-ocean-500 rounded-full animate-spin" />
                  </div>
                  
                  {/* Progress steps */}
                  <div className="space-y-3">
                    {Object.entries(PROGRESS_STEPS).map(([key, { icon: Icon, label, color }]) => {
                      const stepOrder = ['embedding', 'youtube', 'populating', 'filtering', 'scoring', 'done'];
                      const isActive = progress.step === key;
                      const isPast = stepOrder.indexOf(progress.step) > stepOrder.indexOf(key);
                      
                      return (
                        <div 
                          key={key}
                          className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                            isActive ? 'bg-ocean-500/20 border border-ocean-500/30' : 
                            isPast ? 'opacity-50' : 'opacity-30'
                          }`}
                        >
                          <Icon className={`w-5 h-5 ${isActive ? color : 'text-gray-500'}`} />
                          <div className="flex-1">
                            <p className={`text-sm font-medium ${isActive ? 'text-white' : 'text-gray-400'}`}>
                              {label}
                            </p>
                            {isActive && progress.details && (
                              <p className="text-xs text-gray-500 mt-0.5">{progress.details}</p>
                            )}
                          </div>
                          {isPast && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                          {isActive && <div className="w-2 h-2 rounded-full bg-ocean-400 animate-pulse" />}
                        </div>
                      );
                    })}
                  </div>
                  
                  <p className="text-center text-xs text-gray-500 mt-6">
                    First search for a topic takes longer as we fetch data from YouTube
                  </p>
                </div>
              </div>
            )}

            {hasSearched && error && (
              <EmptyState 
                type="error" 
                errorMessage={error}
                onRetry={() => {
                  setError(null);
                  setHasSearched(false);
                }}
              />
            )}

            {hasSearched && !isLoading && !error && results && (
              <>
                {results.creators.length > 0 ? (
                  <>
                    <ResultsHeader
                      query={results.query}
                      totalResults={results.total_results}
                      filteredCount={results.filtered_count}
                      processingTime={results.processing_time_ms}
                      metricsUsed={results.metrics_used}
                    />
                    <div className="space-y-4">
                      {results.creators.map((creator, index) => (
                        <CreatorCard
                          key={creator.id}
                          creator={creator}
                          rank={index + 1}
                        />
                      ))}
                    </div>
                  </>
                ) : (
                  <EmptyState 
                    type="no-results" 
                    query={results.query}
                  />
                )}
              </>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 mt-20">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-500">
            <p>Expert Suitability Engine v1.0</p>
            <p>YouTube Data Only • Public Information • No Scraping</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

