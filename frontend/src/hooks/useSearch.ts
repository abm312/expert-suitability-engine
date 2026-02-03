'use client';

import { useState, useCallback } from 'react';
import { SearchRequest, SearchResponse, MetricType, MetricConfig, FilterConfig, DEFAULT_METRICS } from '@/types';
import { api } from '@/lib/api';

interface UseSearchOptions {
  initialMetrics?: Record<MetricType, MetricConfig>;
  initialFilters?: FilterConfig;
}

export function useSearch(options: UseSearchOptions = {}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [metrics, setMetrics] = useState<Record<MetricType, MetricConfig>>(
    options.initialMetrics || DEFAULT_METRICS
  );
  const [filters, setFilters] = useState<FilterConfig>(
    options.initialFilters || {}
  );

  const search = useCallback(async (query: string, keywords: string[] = []) => {
    setIsLoading(true);
    setError(null);

    const request: SearchRequest = {
      topic_query: query,
      topic_keywords: keywords,
      metrics,
      filters,
      limit: 20,
      offset: 0,
    };

    try {
      const response = await api.searchCreators(request);
      setResults(response);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
      setResults(null);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [metrics, filters]);

  const loadMore = useCallback(async () => {
    if (!results || isLoading) return;

    setIsLoading(true);
    setError(null);

    const request: SearchRequest = {
      topic_query: results.query,
      topic_keywords: [],
      metrics,
      filters,
      limit: 20,
      offset: results.creators.length,
    };

    try {
      const response = await api.searchCreators(request);
      setResults({
        ...response,
        creators: [...results.creators, ...response.creators],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Load more failed');
    } finally {
      setIsLoading(false);
    }
  }, [results, metrics, filters, isLoading]);

  const reset = useCallback(() => {
    setResults(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    // State
    isLoading,
    error,
    results,
    metrics,
    filters,
    
    // Actions
    search,
    loadMore,
    reset,
    setMetrics,
    setFilters,
    
    // Computed
    hasResults: results !== null && results.creators.length > 0,
    hasMore: results !== null && results.creators.length < results.filtered_count,
  };
}

