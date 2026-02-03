'use client';

import { cn } from '@/lib/utils';

interface ScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export function ScoreRing({ score, size = 60, strokeWidth = 4, className }: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score * circumference);
  
  const getColor = (score: number) => {
    if (score >= 0.8) return { stroke: '#34d399', text: 'text-emerald-400', glow: 'shadow-emerald-500/30' };
    if (score >= 0.6) return { stroke: '#38bdf8', text: 'text-ocean-400', glow: 'shadow-ocean-500/30' };
    if (score >= 0.4) return { stroke: '#fbbf24', text: 'text-yellow-400', glow: 'shadow-yellow-500/30' };
    return { stroke: '#f87171', text: 'text-red-400', glow: 'shadow-red-500/30' };
  };

  const colors = getColor(score);
  const scorePercent = Math.round(score * 100);

  return (
    <div 
      className={cn("relative flex items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={strokeWidth}
        />
        {/* Score ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
          style={{
            filter: `drop-shadow(0 0 6px ${colors.stroke}40)`,
          }}
        />
      </svg>
      <div className={cn("absolute inset-0 flex items-center justify-center", colors.text)}>
        <span className="text-lg font-bold">{scorePercent}</span>
      </div>
    </div>
  );
}

