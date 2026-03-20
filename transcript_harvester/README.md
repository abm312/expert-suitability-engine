# Transcript Scraper

Standalone local service for fetching recent YouTube video transcripts for a channel.

This service is intentionally separate from the main Expert Suitability Engine. It can run on its own today, and later the existing webapp can call it over HTTP or import its service layer directly.

## What It Does

- Resolves a YouTube channel from a `channel_id`, channel URL, handle, or search query
- Pulls the channel's recent uploads using the YouTube Data API
- Fetches transcripts for those videos using `youtube-transcript-api`
- Caches channel, video, and transcript data in local SQLite
- Returns transcript dumps as JSON
- Can optionally save dumps to disk

## Quick Start

1. Create a `.env` file in this folder from `.env.example`
2. Install dependencies:

```bash
cd transcript_harvester
../.venv/bin/python -m pip install -r requirements.txt
```

3. Run the API:

```bash
cd transcript_harvester
../.venv/bin/python -m uvicorn app.main:app --reload --port 8100
```

4. Run the CLI:

```bash
cd transcript_harvester
../.venv/bin/python -m app.cli dump --channel-id UC_x5XG1OV2P6uZZ5FSM9Ttw --max-videos 3
```

## Transcript Providers

- `TH_TRANSCRIPT_PROVIDER=auto` prefers Supadata when `TH_SUPADATA_API_KEY` is set, then RapidAPI when `TH_RAPIDAPI_KEY` is set, otherwise it falls back to the local `youtube-transcript-api` library.
- `TH_TRANSCRIPT_PROVIDER=supadata` forces the Supadata provider.
- `TH_TRANSCRIPT_PROVIDER=rapidapi` forces the Solid API RapidAPI provider.
- `TH_TRANSCRIPT_PROVIDER=youtube_transcript_api` forces the local library.
- Reliability knobs:
  - `TH_SUPADATA_MODE` (`auto`, `native`, or `generate`)
  - `TH_SUPADATA_TIMEOUT_SECONDS` (default `30`)
  - `TH_SUPADATA_MAX_ATTEMPTS` (default `3`)
  - `TH_SUPADATA_RETRY_BASE_SECONDS` (default `1`)
  - `TH_SUPADATA_RETRY_MAX_SECONDS` (default `8`)
  - `TH_SUPADATA_POLL_INTERVAL_SECONDS` (default `1`)
  - `TH_SUPADATA_MAX_POLL_ATTEMPTS` (default `90`)
  - `TH_RAPIDAPI_TIMEOUT_SECONDS` (default `10`)
  - `TH_RAPIDAPI_MAX_ATTEMPTS` (default `1`)
  - `TH_RAPIDAPI_RETRY_BASE_SECONDS` (default `1`)
  - `TH_RAPIDAPI_RETRY_MAX_SECONDS` (default `8`)
  - `TH_RAPIDAPI_FALLBACK_TO_AUTO_LANGUAGE` (default `false`)
  - `TH_MISSING_TRANSCRIPT_CACHE_SECONDS` (default `21600`, i.e. 6h)

For Supadata:

```bash
TH_TRANSCRIPT_PROVIDER=supadata
TH_SUPADATA_API_KEY=your_supadata_api_key
TH_SUPADATA_MODE=auto
```

For the RapidAPI provider shown in your dashboard:

```bash
TH_TRANSCRIPT_PROVIDER=rapidapi
TH_RAPIDAPI_KEY=your_rapidapi_key
TH_RAPIDAPI_HOST=youtube-transcript3.p.rapidapi.com
```

## Render Note

- This service includes `.python-version` pinned to `3.12` so Render does not default to Python 3.14, which can force source builds for the older pinned `pydantic` stack.
- If Render still shows Python 3.14 in the build logs for your service, set the service env var `PYTHON_VERSION=3.12.9` and redeploy.
- For stable deployed transcript fetching, set `TH_TRANSCRIPT_PROVIDER=rapidapi` and add `TH_RAPIDAPI_KEY` in Render instead of relying on cloud-IP scraping.

## API Endpoints

- `GET /health`
- `POST /api/v1/transcripts/dump`
- `POST /api/v1/transcripts/download`
- `POST /api/v1/transcripts/analyze`
- `GET /api/v1/channels/{channel_id}/transcripts/cached`

## Why This Fits The Existing Webapp Later

- It accepts `channel_id`, which your current search results already expose
- The dump response is channel-centric and can be attached to creator cards
- The core logic lives in `app/services/harvest_service.py`, so later you can:
  - call this service over HTTP, or
  - move/import the orchestrator into the current backend
