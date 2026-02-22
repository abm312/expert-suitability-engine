'use client';

import { useState } from 'react';
import Image from 'next/image';
import { 
  ExternalLink, 
  TrendingUp, 
  Eye, 
  Users, 
  ChevronDown, 
  ChevronUp,
  Play,
  MessageSquare,
  Star,
  Zap
} from 'lucide-react';
import { CreatorCard as CreatorCardType, MetricType } from '@/types';
import { cn, formatNumber, formatScore, getScoreColor, getScoreBgColor, getGrowthIcon, getLinkIcon, getDomainFromUrl } from '@/lib/utils';
import { ScoreRing } from './ScoreRing';

interface CreatorCardProps {
  creator: CreatorCardType;
  rank: number;
}

const METRIC_LABELS: Record<MetricType, string> = {
  credibility: 'Credibility',
  topic_authority: 'Topic',
  communication: 'Communication',
  freshness: 'Freshness',
  growth: 'Growth',
};

const METRIC_ICONS: Record<MetricType, string> = {
  credibility: '🎯',
  topic_authority: '📚',
  communication: '🎤',
  freshness: '⚡',
  growth: '📈',
};

export function CreatorCard({ creator, rank }: CreatorCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div 
      className={cn(
        "glass-card overflow-hidden transition-all duration-300",
        expanded ? "ring-1 ring-ocean-500/30" : "hover:ring-1 hover:ring-white/10"
      )}
      style={{ animationDelay: `${rank * 100}ms` }}
    >
      {/* Main content */}
      <div className="p-5">
        <div className="flex gap-5">
          {/* Rank & Avatar */}
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-ocean-500 to-ocean-600 flex items-center justify-center font-bold text-sm shadow-lg shadow-ocean-500/30">
              {rank}
            </div>
            <div className="relative">
              {creator.thumbnail_url ? (
                <Image
                  src={creator.thumbnail_url}
                  alt={creator.channel_name}
                  width={64}
                  height={64}
                  className="rounded-xl object-cover"
                />
              ) : (
                <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
                  <span className="text-2xl font-bold text-gray-500">
                    {creator.channel_name[0]}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <a
                  href={creator.channel_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center gap-2 hover:text-ocean-400 transition-colors"
                >
                  <h3 className="text-lg font-semibold truncate">{creator.channel_name}</h3>
                  <ExternalLink className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </a>
                <div className="flex items-center gap-4 mt-1 text-sm text-gray-400">
                  <span className="flex items-center gap-1.5">
                    <Users className="w-4 h-4" />
                    {formatNumber(creator.total_subscribers)}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Eye className="w-4 h-4" />
                    {formatNumber(creator.total_views)}
                  </span>
                  <span className="flex items-center gap-1">
                    {getGrowthIcon(creator.growth_trend)} {creator.growth_trend}
                  </span>
                </div>
              </div>

              {/* Score */}
              <ScoreRing score={creator.overall_score} size={60} />
            </div>

            {/* Score Breakdown - Visual Bars */}
            <div className="space-y-2.5 mt-4">
              {Object.entries(creator.subscores).map(([key, score]) => (
                <div key={key} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-gray-400">
                      <span>{METRIC_ICONS[key as MetricType]}</span>
                      <span>{METRIC_LABELS[key as MetricType]}</span>
                    </span>
                    <span className={cn("font-semibold", getScoreColor(score))}>
                      {formatScore(score)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800/50 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        score >= 80 ? "bg-gradient-to-r from-emerald-500 to-emerald-400" :
                        score >= 60 ? "bg-gradient-to-r from-ocean-500 to-ocean-400" :
                        score >= 40 ? "bg-gradient-to-r from-amber-500 to-amber-400" :
                        "bg-gradient-to-r from-red-500 to-red-400"
                      )}
                      style={{
                        width: `${score}%`,
                        animationDelay: `${(key.charCodeAt(0) % 5) * 100}ms`
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Topic Match */}
            <p className="mt-3 text-sm text-gray-400 flex items-center gap-2">
              <Zap className="w-4 h-4 text-flame-400" />
              {creator.topic_match_summary}
            </p>
          </div>
        </div>

        {/* Why This Expert - Always visible */}
        <div className="mt-5 p-4 bg-slate-800/50 rounded-xl border border-white/5">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-medium text-gray-200">Why This Expert</span>
          </div>
          <ul className="space-y-2.5">
            {creator.why_expert.slice(0, expanded ? undefined : 5).map((reason, i) => (
              <li key={i} className="text-sm text-gray-300 leading-relaxed">
                {reason}
              </li>
            ))}
          </ul>
        </div>

        {/* Expand button */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full mt-4 py-2 flex items-center justify-center gap-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Show more
            </>
          )}
        </button>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 space-y-5 animate-fade-in border-t border-white/5 pt-5">
          {/* Top Videos */}
          {creator.top_videos.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <Play className="w-4 h-4" />
                Top Videos
              </h4>
              <div className="grid gap-3">
                {creator.top_videos.map((video) => (
                  <a
                    key={video.video_id}
                    href={`https://youtube.com/watch?v=${video.video_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-colors group"
                  >
                    {video.thumbnail_url && (
                      <Image
                        src={video.thumbnail_url}
                        alt={video.title}
                        width={80}
                        height={45}
                        className="rounded object-cover flex-shrink-0"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-200 truncate group-hover:text-ocean-400 transition-colors">
                        {video.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatNumber(video.views)} views
                      </p>
                    </div>
                    <ExternalLink className="w-4 h-4 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Call Topics */}
          {creator.suggested_topics.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Suggested Call Topics
              </h4>
              <div className="flex flex-wrap gap-2">
                {creator.suggested_topics.map((topic, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 text-sm rounded-lg border border-emerald-500/20"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* External Links */}
          {creator.external_links.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-3">External Links</h4>
              <div className="flex flex-wrap gap-2">
                {creator.external_links.map((link, i) => (
                  <a
                    key={i}
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 hover:bg-slate-800 rounded-lg text-sm text-gray-400 hover:text-gray-200 transition-colors border border-white/5 hover:border-white/10"
                  >
                    <span>{getLinkIcon(link)}</span>
                    <span>{getDomainFromUrl(link)}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

