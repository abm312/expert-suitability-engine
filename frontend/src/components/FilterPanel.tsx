'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Filter, X } from 'lucide-react';
import { FilterConfig } from '@/types';
import { cn, formatNumber } from '@/lib/utils';

interface FilterPanelProps {
  filters: FilterConfig;
  onChange: (filters: FilterConfig) => void;
}

const SUBSCRIBER_PRESETS = [
  { label: 'Micro (1K-10K)', min: 1000, max: 10000 },
  { label: 'Small (10K-50K)', min: 10000, max: 50000 },
  { label: 'Medium (50K-250K)', min: 50000, max: 250000 },
  { label: 'Large (250K-1M)', min: 250000, max: 1000000 },
  { label: 'Major (1M+)', min: 1000000, max: undefined },
];

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const activeFilterCount = Object.values(filters).filter(v => v !== undefined).length;

  const updateFilter = (key: keyof FilterConfig, value: number | undefined) => {
    onChange({ ...filters, [key]: value });
  };

  const clearFilters = () => {
    onChange({});
  };

  const applyPreset = (min: number | undefined, max: number | undefined) => {
    onChange({
      ...filters,
      subscriber_min: min,
      subscriber_max: max,
    });
  };

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-flame-500/20 flex items-center justify-center">
            <Filter className="w-4 h-4 text-flame-400" />
          </div>
          <span className="font-medium text-gray-200">Filters</span>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-flame-500/20 text-flame-400 rounded-full">
              {activeFilterCount}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-5 animate-fade-in">
          {/* Subscriber Range */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-300">Subscriber Range</label>
            <div className="flex flex-wrap gap-2">
              {SUBSCRIBER_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => applyPreset(preset.min, preset.max)}
                  className={cn(
                    "px-3 py-1.5 text-xs rounded-lg border transition-all",
                    filters.subscriber_min === preset.min && filters.subscriber_max === preset.max
                      ? "bg-ocean-500/20 border-ocean-500/50 text-ocean-300"
                      : "bg-slate-800/50 border-white/5 text-gray-400 hover:border-white/20"
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <input
                type="number"
                placeholder="Min"
                value={filters.subscriber_min || ''}
                onChange={(e) => updateFilter('subscriber_min', e.target.value ? parseInt(e.target.value) : undefined)}
                className="input-field text-sm"
              />
              <span className="text-gray-500">to</span>
              <input
                type="number"
                placeholder="Max"
                value={filters.subscriber_max || ''}
                onChange={(e) => updateFilter('subscriber_max', e.target.value ? parseInt(e.target.value) : undefined)}
                className="input-field text-sm"
              />
            </div>
          </div>

          {/* Video Length */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Min Avg Video Length (minutes)</label>
            <input
              type="number"
              placeholder="e.g., 8"
              value={filters.avg_video_length_min ? filters.avg_video_length_min / 60 : ''}
              onChange={(e) => updateFilter('avg_video_length_min', e.target.value ? parseInt(e.target.value) * 60 : undefined)}
              className="input-field text-sm"
            />
          </div>

          {/* Growth Rate */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Min Growth Rate (%)</label>
            <input
              type="number"
              placeholder="e.g., 5"
              value={filters.growth_rate_min || ''}
              onChange={(e) => updateFilter('growth_rate_min', e.target.value ? parseFloat(e.target.value) : undefined)}
              className="input-field text-sm"
            />
          </div>

          {/* Recent Uploads */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Min Uploads (last 90 days)</label>
            <input
              type="number"
              placeholder="e.g., 3"
              value={filters.uploads_last_90_days_min || ''}
              onChange={(e) => updateFilter('uploads_last_90_days_min', e.target.value ? parseInt(e.target.value) : undefined)}
              className="input-field text-sm"
            />
          </div>

          {/* Topic Relevance */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Min Topic Relevance (0-1)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              placeholder="e.g., 0.5"
              value={filters.topic_relevance_min || ''}
              onChange={(e) => updateFilter('topic_relevance_min', e.target.value ? parseFloat(e.target.value) : undefined)}
              className="input-field text-sm"
            />
          </div>

          {/* Clear Filters */}
          {activeFilterCount > 0 && (
            <button
              onClick={clearFilters}
              className="w-full flex items-center justify-center gap-2 py-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              <X className="w-4 h-4" />
              Clear all filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}

