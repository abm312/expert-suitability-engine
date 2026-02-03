import { SearchRequest, SearchResponse, CreatorCard } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://ese-backend-61as.onrender.com/api/v1';

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
};

export { APIError };

