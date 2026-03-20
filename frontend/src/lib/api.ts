import {
  SearchRequest,
  SearchResponse,
  CreatorCard,
  TranscriptDumpResponse,
  CommunicationAnalysisResponse,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://ese-backend-61as.onrender.com/api/v1';
const LOCAL_TRANSCRIPT_API_BASE = 'http://127.0.0.1:8100/api/v1';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new APIError(response.status, error.detail || 'Request failed');
    }

    return response.json();
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new APIError(0, 'Cannot connect to server. Make sure the backend is running on port 8000.');
    }
    throw err;
  }
}

function getTranscriptApiBase(): string | null {
  if (process.env.NEXT_PUBLIC_TRANSCRIPT_API_URL) {
    return process.env.NEXT_PUBLIC_TRANSCRIPT_API_URL;
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return LOCAL_TRANSCRIPT_API_BASE;
    }
  }

  return null;
}

function parseDownloadFilename(
  contentDisposition: string | null,
  fallback: string
): string {
  if (!contentDisposition) {
    return fallback;
  }

  const match = contentDisposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] || fallback;
}

export const api = {
  // Health check
  health: () => fetchAPI<{ status: string }>('/health'),

  // Search creators
  searchCreators: (request: SearchRequest) =>
    fetchAPI<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  // List creators
  listCreators: (params?: { limit?: number; offset?: number; sort_by?: string }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    if (params?.sort_by) query.set('sort_by', params.sort_by);
    return fetchAPI<{ creators: CreatorCard[]; limit: number; offset: number }>(
      `/creators?${query}`
    );
  },

  // Get creator detail
  getCreator: (id: number, topicQuery?: string) => {
    const query = topicQuery ? `?topic_query=${encodeURIComponent(topicQuery)}` : '';
    return fetchAPI<any>(`/creators/${id}${query}`);
  },

  // Discover new creators
  discoverCreators: (searchQuery: string, maxResults: number = 50) =>
    fetchAPI<{ status: string; added_count: number; creators: any[] }>('/discover', {
      method: 'POST',
      body: JSON.stringify({ search_query: searchQuery, max_results: maxResults }),
    }),

  // Refresh creator data
  refreshCreator: (id: number) =>
    fetchAPI<{ status: string }>(`/creators/${id}/refresh`, {
      method: 'POST',
    }),

  // Get available metrics
  getMetrics: () =>
    fetchAPI<{ metrics: any[] }>('/metrics'),

  // Get available filters
  getFilters: () =>
    fetchAPI<{ filters: any[] }>('/filters'),

  // Get search progress
  getProgress: () =>
    fetchAPI<{ status: string; step: string; details: string }>('/progress'),

  // Resolve transcript service base URL (local-only unless explicitly configured)
  getTranscriptApiBase,

  // Fetch transcript dump JSON from the standalone transcript service
  fetchTranscriptDump: async (params: { channelId: string; maxVideos: number }) => {
    const transcriptBase = getTranscriptApiBase();

    if (!transcriptBase) {
      throw new APIError(
        0,
        'Transcript scraper is only available when NEXT_PUBLIC_TRANSCRIPT_API_URL is configured.'
      );
    }

    let response: Response;
    try {
      response = await fetch(`${transcriptBase}/transcripts/dump`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          channel_id: params.channelId,
          max_videos: params.maxVideos,
          languages: ['en'],
          refresh: false,
          persist_dump_file: false,
        }),
      });
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new APIError(
          0,
          'Cannot reach the transcript scraper service. Make sure it is running and reachable.'
        );
      }
      throw err;
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Transcript scraper request failed' }));
      throw new APIError(response.status, error.detail || 'Transcript scraper request failed');
    }

    return response.json() as Promise<TranscriptDumpResponse>;
  },

  analyzeTranscriptCommunication: async (dump: TranscriptDumpResponse) => {
    const transcriptBase = getTranscriptApiBase();

    if (!transcriptBase) {
      throw new APIError(
        0,
        'Transcript scraper is only available when NEXT_PUBLIC_TRANSCRIPT_API_URL is configured.'
      );
    }

    let response: Response;
    try {
      response = await fetch(`${transcriptBase}/transcripts/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(dump),
      });
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new APIError(
          0,
          'Cannot reach the transcript scraper service. Make sure it is running and reachable.'
        );
      }
      throw err;
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Communication analysis failed' }));
      throw new APIError(response.status, error.detail || 'Communication analysis failed');
    }

    return response.json() as Promise<CommunicationAnalysisResponse>;
  },

  downloadTranscriptDump: async (params: { channelId: string; maxVideos: number }) => {
    const transcriptBase = getTranscriptApiBase();

    if (!transcriptBase) {
      throw new APIError(
        0,
        'Transcript scraper is only available when NEXT_PUBLIC_TRANSCRIPT_API_URL is configured.'
      );
    }

    let response: Response;
    try {
      response = await fetch(`${transcriptBase}/transcripts/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          channel_id: params.channelId,
          max_videos: params.maxVideos,
          languages: ['en'],
          refresh: false,
          persist_dump_file: false,
        }),
      });
    } catch (err) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new APIError(
          0,
          'Cannot reach the transcript scraper service. Make sure it is running and reachable.'
        );
      }
      throw err;
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Transcript scraper request failed' }));
      throw new APIError(response.status, error.detail || 'Transcript scraper request failed');
    }

    const blob = await response.blob();
    const fallbackName = `${params.channelId}-transcripts.json`;
    const filename = parseDownloadFilename(
      response.headers.get('Content-Disposition'),
      fallbackName
    );

    return { blob, filename };
  },
};

export { APIError };
