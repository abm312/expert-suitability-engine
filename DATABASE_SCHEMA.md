# Database Schema & API Data Flow

## Database Schema

### Table 1: `creators`
**Stores channel-level information**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing primary key |
| `channel_id` | String(50) | YouTube channel ID (unique) |
| `channel_name` | String(255) | Channel display name |
| `channel_description` | Text | Full channel description |
| `created_at` | DateTime | When record was created in DB |
| `total_subscribers` | BigInteger | Current subscriber count |
| `total_views` | BigInteger | Total lifetime views |
| `total_videos` | Integer | Total video count |
| `channel_created_date` | DateTime | When channel was created on YouTube |
| `external_links` | JSON | Array of URLs (GitHub, LinkedIn, etc.) |
| `thumbnail_url` | String(500) | Channel thumbnail image URL |
| `country` | String(50) | Channel country code |
| `last_fetched_at` | DateTime | Last time data was refreshed from YouTube |
| `credibility_score` | Float | Cached credibility metric (0-1) |
| `topic_score` | Float | Cached topic authority metric (0-1) |
| `communication_score` | Float | Cached communication metric (0-1) |
| `freshness_score` | Float | Cached freshness metric (0-1) |
| `growth_score` | Float | Cached growth metric (0-1) |
| `overall_score` | Float | Cached overall suitability score (0-1) |

**Relationships:**
- Has many `videos`
- Has many `metrics_snapshots`

---

### Table 2: `videos`
**Stores individual video information**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing primary key |
| `creator_id` | Integer (FK) | References `creators.id` |
| `video_id` | String(50) | YouTube video ID (unique) |
| `title` | String(500) | Video title |
| `description` | Text | Full video description |
| `published_at` | DateTime | When video was published |
| `duration_seconds` | Integer | Video length in seconds |
| `views` | BigInteger | Total view count |
| `likes` | BigInteger | Total like count |
| `comments` | BigInteger | Total comment count |
| `has_captions` | Boolean | Whether captions are available |
| `thumbnail_url` | String(500) | Video thumbnail image URL |
| `tags` | JSON | Array of video tags |
| `fetched_at` | DateTime | When data was fetched from YouTube |

**Relationships:**
- Belongs to one `creator`
- Has one `transcript` (optional)

---

### Table 3: `transcripts`
**Stores video transcript text and embeddings**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing primary key |
| `video_id` | Integer (FK) | References `videos.id` (unique) |
| `text` | Text | Full transcript text |
| `language` | String(10) | Language code (default: "en") |
| `embedding` | Vector(1536) | OpenAI embedding vector for semantic search |
| `created_at` | DateTime | When transcript was created |

**Relationships:**
- Belongs to one `video`

**Note:** Currently transcripts are NOT fetched (would require additional API calls). This table exists for future use.

---

### Table 4: `metrics_snapshots`
**Historical tracking of channel metrics over time**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing primary key |
| `creator_id` | Integer (FK) | References `creators.id` |
| `date` | Date | Snapshot date |
| `subscriber_count` | BigInteger | Subscribers on this date |
| `view_count` | BigInteger | Total views on this date |
| `video_count` | Integer | Total videos on this date |

**Relationships:**
- Belongs to one `creator`

**Purpose:** Used to calculate growth trajectory (30/90/180 day growth rates)

---

### Table 5: `search_queries`
**Stores search queries for analytics (optional)**

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-incrementing primary key |
| `query_text` | String(500) | The search query text |
| `topic_embedding` | Vector(1536) | Embedding of the search query |
| `filters` | JSON | Applied filters (subscriber range, etc.) |
| `weights` | JSON | Metric weights used |
| `created_at` | DateTime | When search was performed |
| `results_count` | Integer | Number of results returned |

---

## 🔄 What Data the API Pulls from YouTube

### Step 1: Channel Search (`search_channels`)
**API Call:** `youtube.search().list(type="channel")`

**Pulls:**
- ✅ `channel_id` - YouTube channel ID
- ✅ `channel_name` - Channel title
- ✅ `description` - Channel description snippet
- ✅ `thumbnail_url` - Channel thumbnail

**Used for:** Initial discovery of channels matching search query

---

### Step 2: Channel Details (`get_channel_details`)
**API Call:** `youtube.channels().list(part="snippet,statistics,brandingSettings,topicDetails")`

**Pulls:**
- ✅ `channel_id` - YouTube channel ID
- ✅ `channel_name` - Full channel title
- ✅ `channel_description` - Full description
- ✅ `total_subscribers` - Current subscriber count
- ✅ `total_views` - Lifetime view count
- ✅ `total_videos` - Total video count
- ✅ `channel_created_date` - Channel creation date
- ✅ `thumbnail_url` - High-res thumbnail
- ✅ `country` - Channel country code
- ✅ `external_links` - Extracted from description (GitHub, LinkedIn, etc.)
- ✅ `keywords` - Channel keywords
- ✅ `topic_categories` - YouTube topic categories

**Stored in:** `creators` table

---

### Step 3: Channel Videos (`get_channel_videos`)
**API Call 1:** `youtube.channels().list(part="contentDetails")` - Get uploads playlist
**API Call 2:** `youtube.playlistItems().list()` - Get video IDs from playlist
**API Call 3:** `youtube.videos().list(part="snippet,statistics,contentDetails")` - Get video details

**Pulls (per video):**
- ✅ `video_id` - YouTube video ID
- ✅ `title` - Video title
- ✅ `description` - Full video description
- ✅ `published_at` - Publication date
- ✅ `duration_seconds` - Video length
- ✅ `views` - View count
- ✅ `likes` - Like count
- ✅ `comments` - Comment count
- ✅ `has_captions` - Whether captions exist
- ✅ `thumbnail_url` - Video thumbnail
- ✅ `tags` - Array of video tags

**Stored in:** `videos` table

**Limit:** Fetches up to 20 videos per channel (configurable)

---

## 📥 Data Flow: YouTube API → Database → Metrics

```
1. USER SEARCHES: "machine learning expert"
   │
   ▼
2. YouTube API: search_channels()
   → Returns list of channel IDs matching query
   │
   ▼
3. For each channel:
   │
   ├─→ YouTube API: get_channel_details()
   │   → Stores in `creators` table
   │
   └─→ YouTube API: get_channel_videos()
       → Stores in `videos` table (up to 20 videos)
   │
   ▼
4. Database now has:
   - Creator profile (subscribers, views, description, links)
   - Recent videos (titles, descriptions, tags, stats)
   │
   ▼
5. Metrics Calculation:
   │
   ├─→ Credibility Metric
   │   Uses: channel_created_date, video durations, upload gaps, external_links
   │
   ├─→ Topic Authority Metric
   │   Uses: video titles, descriptions, tags → generates embeddings → compares to search query
   │
   ├─→ Freshness Metric
   │   Uses: video published_at dates
   │
   ├─→ Growth Metric
   │   Uses: metrics_snapshots (if available) or current subscriber count
   │
   └─→ Communication Metric
       Uses: transcripts (currently disabled - no transcripts fetched)
   │
   ▼
6. Results returned to frontend with scores and explanations
```

---

## 🔍 What Data is NOT Pulled

**Currently NOT fetched:**
- ❌ Video transcripts (would require additional API calls)
- ❌ Video comments (not needed for metrics)
- ❌ Channel playlists (only uploads playlist is used)
- ❌ Channel memberships/subscriptions
- ❌ Live stream data
- ❌ Community posts

**Why?**
- Transcripts would require extra API calls and cost
- Other data not needed for v1 metrics
- Focus on public, easily accessible data

---

## 📊 Example Data Structure

### Creator Record Example:
```json
{
  "id": 1,
  "channel_id": "UC1234567890",
  "channel_name": "AI Explained",
  "channel_description": "Deep dives into machine learning...",
  "total_subscribers": 125000,
  "total_views": 5000000,
  "total_videos": 150,
  "channel_created_date": "2020-01-15T00:00:00",
  "external_links": [
    "https://github.com/aiexplained",
    "https://twitter.com/aiexplained"
  ],
  "country": "US",
  "last_fetched_at": "2024-01-20T10:30:00"
}
```

### Video Record Example:
```json
{
  "id": 1,
  "creator_id": 1,
  "video_id": "dQw4w9WgXcQ",
  "title": "Understanding Transformers: Attention is All You Need",
  "description": "In this video, we explore...",
  "published_at": "2024-01-10T14:00:00",
  "duration_seconds": 1200,
  "views": 50000,
  "likes": 2500,
  "comments": 300,
  "has_captions": true,
  "tags": ["machine learning", "transformers", "AI", "deep learning"]
}
```

---

## 🎯 Key Points

1. **Discovery:** YouTube search finds channels → stores basic info
2. **Enrichment:** For each channel, fetch full details + recent videos
3. **Storage:** All data stored in PostgreSQL for fast retrieval
4. **Metrics:** Calculated on-the-fly using stored data
5. **Embeddings:** Generated from video titles/descriptions/tags (not transcripts)
6. **Growth Tracking:** `metrics_snapshots` table tracks historical data (populated over time)

---

## 🔄 Data Refresh Strategy

**Current behavior:**
- On each search, new channels are discovered and added
- Existing channels are NOT automatically refreshed
- `last_fetched_at` tracks when data was last pulled

**Future enhancement:**
- Could refresh channels older than X days
- Could update `metrics_snapshots` periodically to track growth
