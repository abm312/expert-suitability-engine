# Expert Suitability Engine - Session Notes
**Date:** February 22, 2026

## Session Summary

This session focused on UI/UX improvements and fixing inaccurate claims on the landing page.

---

## Changes Made

### 1. Navigation & Icon Updates (Commit: 10ee135)
- Made header logo/title clickable to return to landing page
- Added `handleReset()` function to clear search state
- Replaced all "Sparkles" icons with simple "Search" icons throughout the app
- **Why:** User wanted way to return to landing page and felt sparkles looked "AI-generated"

### 2. Technical Documentation Created
- Created shortened technical reference: `~/Downloads/SCORING_SYSTEM_TECHNICAL.md`
- Condensed from 1200-line docx to ~400 lines
- Kept all formulas, thresholds, and algorithms
- Removed verbose explanations
- **Source:** `~/Downloads/TECHNICAL_SCORING_EXPLANATION.docx`

### 3. Landing Page Copy - Technical Language (Commit: 72d612b)
- Updated hero text to be more technical
- Updated 3 feature boxes with technical terminology:
  - "5-Metric Composite Algorithm" with normalized weighted scoring
  - "YouTube Data API Integration" with quantitative analysis
  - "Vector-Based Rankings" with cosine similarity

### 4. Removed Transcript NLP Claim (Commit: 18ab0f8)
- **Issue:** Landing page mentioned "transcript NLP" but app doesn't analyze transcripts
- **Fix:** Removed mention from YouTube Data API Integration box
- Now reads: "Quantitative analysis of channel statistics, content embeddings, and engagement metrics via YouTube Data API v3"

### 5. Shortened Hero Copy (Commit: 7dfa714)
- **Before:** "Multi-dimensional weighted scoring algorithm for expert network consulting. Semantic embeddings, quantitative metrics, and real-time data analysis to identify optimal subject matter experts."
- **After:** "Weighted scoring across 5 metrics using semantic embeddings and YouTube API data to rank subject matter experts."
- **Why:** Sounded too "AI-generated"

### 6. Footer Cleanup (Commit: 1534381)
- Removed "v1.0" from "Expert Suitability Engine"
- Removed "No Scraping" mention
- Footer now: "Expert Suitability Engine" | "YouTube Data Only • Public Information"

### 7. Prominent Documentation Link (Commit: 065b231)
- Moved scoring documentation link from footer to between search box and feature blocks
- Styled as prominent button: "Understand Scoring Criteria Here"
- Uses Database icon with ocean color scheme
- Links to: https://docs.google.com/document/d/1fFDbD6vgfRFUJBQ3Ez3t4ZysKnnksopPrCs_aCI82I8/edit?usp=sharing

---

## Outstanding Issues from Previous Session

### Backend Health Check Timeouts
- **Issue:** Backend fails health checks during startup (5-second timeout too short)
- **Cause:** Migrations + app startup takes 10-15 seconds
- **Fix Required:** Manual configuration in Render Dashboard
  - Go to: Settings → Health Check
  - Increase timeout to 30 seconds
- **Note:** Cannot be configured via `render.yaml`

### Recent Backend Changes (Previous Session)
- Added `greenlet` dependency to fix crashes
- Limited scoring to 50 creators max (was 164, causing timeouts)
- Improved logging for diagnostics

---

## File Structure

### Frontend
- **`frontend/src/app/page.tsx`** - Main landing page (all UI changes)
- **`frontend/Dockerfile`** - Frontend deployment config

### Backend
- **`backend/Dockerfile`** - Backend deployment config
- **`backend/requirements.txt`** - Python dependencies

### Deployment
- **`render.yaml`** - Render deployment configuration
  - Database: `ese-db` (PostgreSQL 15, Oregon, Free)
  - Backend: `ese-backend` (Docker, Oregon, Free)
  - Frontend: `ese-frontend` (Docker, Oregon, Free)

### Documentation
- **`~/Downloads/SCORING_SYSTEM_TECHNICAL.md`** - Shortened technical reference
- **Google Doc** - Full technical scoring documentation (linked in app)

---

## Technical Details

### 5-Metric Scoring System
1. **Topic Authority (30%)** - OpenAI embeddings + cosine similarity
2. **Credibility (20%)** - Channel age, video length, upload consistency, external links
3. **Communication (20%)** - Requires transcripts (NOT CURRENTLY IMPLEMENTED)
4. **Freshness (15%)** - Recent activity, last upload, momentum
5. **Growth (15%)** - Subscriber growth, acceleration

### Tech Stack
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy
- **APIs:** YouTube Data API v3, OpenAI API (text-embedding-ada-002)
- **Deployment:** Render (all services on free tier)

### Key Formulas
- **Final Score:** Σ (Metric Score × Normalized Weight)
- **Cosine Similarity:** cos(A,B) = (A·B) / (||A|| × ||B||)
- **Similarity Transform:** f(x) = min(1.0, max(0.0, (x + 0.2) × 1.25))

---

## Git History (This Session)

```
065b231 - Make scoring documentation more prominent
1534381 - Clean up footer text
7dfa714 - Shorten hero copy and add doc link to footer
18ab0f8 - Remove transcript NLP claim from landing page
72d612b - Update landing page copy to be more technical
10ee135 - Make header clickable and replace sparkles with search icons
```

---

## Current State

### Live URLs
- **Frontend:** https://ese-frontend-dk65.onrender.com
- **Backend:** https://ese-backend-2zyv.onrender.com
- **GitHub:** https://github.com/abm312/expert-suitability-engine

### Next Steps (If Needed)
1. Implement transcript analysis if Communication metric should be used
2. Increase Render health check timeout to 30 seconds (manual dashboard step)
3. Monitor backend stability after health check adjustment

---

## Notes

- All changes pushed to GitHub main branch
- Render auto-deploys on push (takes 2-3 minutes)
- Backend on free tier may spin down after inactivity (30-second cold start)
- Database limited to 1GB on free tier
- All metrics except Communication are working
- Communication metric requires YouTube transcript API integration (future work)
