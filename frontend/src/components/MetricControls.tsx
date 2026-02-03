'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ToggleLeft, ToggleRight, Info } from 'lucide-react';
import { MetricType, MetricConfig, METRIC_INFO } from '@/types';
import { cn } from '@/lib/utils';

interface MetricControlsProps {
  metrics: Record<MetricType, MetricConfig>;
  onChange: (metrics: Record<MetricType, MetricConfig>) => void;
}

export function MetricControls({ metrics, onChange }: MetricControlsProps) {
  const [expanded, setExpanded] = useState(false);

  const handleToggle = (metricId: MetricType) => {
    onChange({
      ...metrics,
      [metricId]: {
        ...metrics[metricId],
        enabled: !metrics[metricId].enabled,
      },
    });
  };

  const handleWeightChange = (metricId: MetricType, weight: number) => {
    onChange({
      ...metrics,
      [metricId]: {
        ...metrics[metricId],
        weight: weight / 100,
      },
    });
  };

  // Normalize weights to show percentages
  const totalWeight = Object.values(metrics)
    .filter(m => m.enabled)
    .reduce((sum, m) => sum + m.weight, 0);

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-ocean-500/20 flex items-center justify-center">
            <svg className="w-4 h-4 text-ocean-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20V10" />
              <path d="M18 20V4" />
              <path d="M6 20v-4" />
            </svg>
          </div>
          <span className="font-medium text-gray-200">Metric Weights</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 animate-fade-in">
          {METRIC_INFO.map((info) => {
            const config = metrics[info.id];
            const normalizedWeight = config.enabled && totalWeight > 0
              ? (config.weight / totalWeight) * 100
              : 0;

            return (
              <div key={info.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleToggle(info.id)}
                      className={cn(
                        "transition-colors",
                        config.enabled ? "text-ocean-400" : "text-gray-600"
                      )}
                    >
                      {config.enabled ? (
                        <ToggleRight className="w-6 h-6" />
                      ) : (
                        <ToggleLeft className="w-6 h-6" />
                      )}
                    </button>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          "font-medium transition-colors",
                          config.enabled ? "text-gray-200" : "text-gray-500"
                        )}>
                          {info.name}
                        </span>
                        <div className="group relative">
                          <Info className="w-3.5 h-3.5 text-gray-500 cursor-help" />
                          <div className="absolute left-0 bottom-full mb-2 w-48 p-2 bg-slate-800 rounded-lg text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                            {info.description}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <span className={cn(
                    "text-sm font-mono",
                    config.enabled ? "text-ocean-400" : "text-gray-600"
                  )}>
                    {normalizedWeight.toFixed(0)}%
                  </span>
                </div>

                {config.enabled && (
                  <div className="pl-9">
                    <input
                      type="range"
                      min="5"
                      max="50"
                      value={config.weight * 100}
                      onChange={(e) => handleWeightChange(info.id, parseInt(e.target.value))}
                      className="w-full h-1.5 bg-slate-700 rounded-full appearance-none cursor-pointer
                                 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                                 [&::-webkit-slider-thumb]:bg-ocean-500 [&::-webkit-slider-thumb]:rounded-full
                                 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-ocean-500/50
                                 [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-transform
                                 [&::-webkit-slider-thumb]:hover:scale-110"
                    />
                  </div>
                )}
              </div>
            );
          })}

          <div className="pt-3 border-t border-white/5">
            <p className="text-xs text-gray-500 text-center">
              Weights are normalized. Only enabled metrics contribute to the final score.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

