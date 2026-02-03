export type MetricType = 
  | 'credibility'
  | 'topic_authority'
  | 'communication'
  | 'freshness'
  | 'growth';

export interface MetricConfig {
  enabled: boolean;
  weight: number;
}

export interface FilterConfig {
  subscriber_min?: number;
  subscriber_max?: number;
  avg_video_length_min?: number;
  growth_rate_min?: number;
  uploads_last_90_days_min?: number;
  topic_relevance_min?: number;
}

export interface SearchRequest {
  topic_query: string;
  topic_keywords: string[];
  metrics: Record<MetricType, MetricConfig>;
  filters: FilterConfig;
  limit: number;
  offset: number;
}

export interface VideoSummary {
  video_id: string;
  title: string;
  views: number;
  thumbnail_url?: string;
}

export interface RelevantContent {
  title: string;
  url: string;
  relevance: string;
  views?: number;
}

export interface CreatorCard {
  id: number;
  channel_id: string;
  channel_name: string;
  thumbnail_url?: string;
  total_subscribers: number;
  total_views: number;
  overall_score: number;
  subscores: Record<MetricType, number>;
  why_expert: string[];
  topic_match_summary: string;
  top_videos: VideoSummary[];
  relevant_content: RelevantContent[];
  suggested_topics: string[];
  growth_trend: string;
  external_links: string[];
  channel_url: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  filtered_count: number;
  creators: CreatorCard[];
  metrics_used: string[];
  filters_applied: Record<string, any>;
  processing_time_ms: number;
}

export interface MetricInfo {
  id: MetricType;
  name: string;
  description: string;
  default_weight: number;
}

export const DEFAULT_METRICS: Record<MetricType, MetricConfig> = {
  credibility: { enabled: true, weight: 0.25 },
  topic_authority: { enabled: true, weight: 0.35 },
  communication: { enabled: false, weight: 0.0 },  // Disabled - requires transcripts
  freshness: { enabled: true, weight: 0.2 },
  growth: { enabled: true, weight: 0.2 },
};

export const METRIC_INFO: MetricInfo[] = [
  {
    id: 'credibility',
    name: 'Credibility',
    description: 'Channel age, video depth, GitHub/social links',
    default_weight: 0.25,
  },
  {
    id: 'topic_authority',
    name: 'Topic Match',
    description: 'How well their content matches your search',
    default_weight: 0.35,
  },
  {
    id: 'communication',
    name: 'Communication',
    description: '⚠️ Requires transcripts (not available)',
    default_weight: 0.0,
  },
  {
    id: 'freshness',
    name: 'Freshness',
    description: 'How recently they post content',
    default_weight: 0.2,
  },
  {
    id: 'growth',
    name: 'Growth',
    description: 'Subscriber growth and momentum',
    default_weight: 0.2,
  },
];

