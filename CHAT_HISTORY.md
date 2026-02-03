# Deployment Chat History - Expert Suitability Engine

**Date**: February 2-3, 2026
**Task**: Deploy Expert Suitability Engine webapp to production

## What We Accomplished

✅ Pushed codebase to GitHub: https://github.com/abm312/expert-suitability-engine
✅ Deployed to Render (free tier)
✅ Fixed 4 critical deployment issues
✅ App is now live and working at: https://ese-frontend-dk65.onrender.com

## Live URLs
- **Frontend**: https://ese-frontend-dk65.onrender.com
- **Backend**: https://ese-backend-61as.onrender.com/api/v1
- **Backend Health**: https://ese-backend-61as.onrender.com/api/v1/health
- **GitHub**: https://github.com/abm312/expert-suitability-engine

## Timeline of Changes

### 1. Git Setup and Security
**Files Changed**:
- Created `.gitignore`
- Removed exposed API keys from `MANUAL.md`

**Commands**:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/abm312/expert-suitability-engine.git
git push -u origin main
```

**⚠️ CRITICAL SECURITY ISSUE FOUND**:
Found hardcoded API keys in `MANUAL.md`:
- YouTube API Key: AIzaSyC*** (REDACTED - was exposed in git history)
- OpenAI API Key: sk-proj-*** (REDACTED - was exposed in git history)

**Action Taken**: Removed from file, replaced with placeholders
**TODO**: You need to rotate these keys immediately at YouTube/OpenAI dashboards

### 2. Created Render Blueprint
**File Created**: `render.yaml`

Defined 3 services:
- `ese-db` - PostgreSQL 15 with pgvector
- `ese-backend` - FastAPI backend (Docker)
- `ese-frontend` - Next.js frontend (Docker)

### 3. Fixed Deployment Issues

#### Issue #1: Invalid Render Blueprint
**Error**: "services[0] docker runtime must not have startCommand"

**Fix**: Removed `startCommand` from `render.yaml` - Docker uses CMD from Dockerfile

**Commit**: `53efb9e`

#### Issue #2: Frontend Empty Public Folder
**Error**: Frontend Docker build failed - "COPY /app/public failed: not found"

**File**: `frontend/Dockerfile` line 31
**Before**:
```dockerfile
COPY --from=builder /app/public ./public
```

**After**:
```dockerfile
RUN mkdir -p ./public && chown nextjs:nodejs ./public
```

**Commit**: `cdcfcc5`

#### Issue #3: Async Database Driver Mismatch
**Error**: "The asyncio extension requires an async driver. The loaded 'psycopg2' is not async"

**File**: `backend/app/db/database.py`
**Fix**: Added URL conversion from `postgres://` to `postgresql+asyncpg://`

**Code Added**:
```python
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url, ...)
```

**Commit**: `56b3097`

#### Issue #4: CORS Blocking Production Frontend
**Error**: CORS errors in browser - backend rejecting frontend requests

**File**: `backend/app/main.py`
**Fix**: Added production frontend URL to allowed origins

**Code Added**:
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ese-frontend-dk65.onrender.com",  # Added this
]
```

**Commit**: `aea36b8`

#### Issue #5: Environment Variables Not Working
**Error**: Frontend still connecting to `localhost:8000` instead of production backend

**Root Cause**: Next.js bakes `NEXT_PUBLIC_*` vars at build time, but Render's Docker build doesn't receive environment variables

**File**: `frontend/src/lib/api.ts` line 3
**Fix**: Hardcoded production backend URL as fallback

**Before**:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
```

**After**:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://ese-backend-61as.onrender.com/api/v1';
```

**Commit**: `5815d37`

**Why This Works**: The hardcoded URL is used as fallback when env var isn't available during Docker build

**⚠️ Important**: If you change backend URL in the future, you MUST update this hardcoded value

### 4. Documentation
Created two documentation files:

**`DEPLOYMENT.md`** - Full deployment guide
- Tech stack overview
- All 5 issues and fixes
- How to run locally
- Troubleshooting guide
- Environment variables

**`CHAT_HISTORY.md`** - This file

**Commits**: `9cddc45`, `c40b87e`

## Key Learnings

1. **Render Docker builds don't get env vars by default** - Need to use build args or hardcode values
2. **Next.js requires `NEXT_PUBLIC_*` at build time** - Not runtime like regular env vars
3. **Render provides `postgres://` URLs** - Need to convert to `postgresql+asyncpg://` for async SQLAlchemy
4. **CORS must include production URLs** - localhost isn't enough
5. **Free tier services sleep after 15 min** - First request takes ~30 seconds to wake up

## How to Make Future Changes

### Normal Development Workflow
1. Make changes locally
2. Test (optional):
   ```bash
   cd frontend && npm run dev  # Uses production backend
   # OR create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```
3. Commit and push:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```
4. Render auto-detects and redeploys (2-5 minutes)

### If Backend URL Changes
If Render gives you a new backend URL:

1. Update `frontend/src/lib/api.ts` line 3:
   ```typescript
   const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://NEW-URL.onrender.com/api/v1';
   ```

2. Update `backend/app/main.py` CORS if frontend URL also changed:
   ```python
   allow_origins=[
       "http://localhost:3000",
       "http://127.0.0.1:3000",
       "https://NEW-FRONTEND-URL.onrender.com",
   ]
   ```

3. Commit and push

### If You Want Proper Env Vars (Not Tested Yet)
See the "⚠️ CRITICAL: Hardcoded Backend URL" section in `DEPLOYMENT.md`

## Files Modified Summary

| File | Purpose | Key Change |
|------|---------|------------|
| `.gitignore` | Prevent committing secrets | Created new |
| `MANUAL.md` | Setup instructions | Removed exposed API keys |
| `render.yaml` | Infrastructure config | Removed startCommand |
| `frontend/Dockerfile` | Frontend build | Create empty public dir |
| `backend/Dockerfile` | Backend build | Run migrations on startup |
| `backend/app/db/database.py` | Database connection | Convert postgres:// URL |
| `backend/app/main.py` | Backend server | Add production CORS |
| `frontend/src/lib/api.ts` | API client | Hardcode backend URL |
| `DEPLOYMENT.md` | Deployment guide | Created new |
| `CHAT_HISTORY.md` | This file | Created new |

## All Commits
```
c40b87e - Add detailed section on hardcoded backend URL and how to change it
9cddc45 - Add deployment documentation
5815d37 - Temporary fix: hardcode production backend URL
aea36b8 - Fix CORS - allow production frontend URL
56b3097 - Fix async database driver - convert postgres URL to postgresql+asyncpg
cdcfcc5 - Fix frontend Dockerfile - handle empty public folder
53efb9e - Fix Render deployment config - remove startCommand for Docker runtime
```

## Testing Checklist

After any deployment:
1. Check Render dashboard - both services should show "Live"
2. Test backend health: https://ese-backend-61as.onrender.com/api/v1/health
3. Open frontend: https://ese-frontend-dk65.onrender.com
4. Open browser DevTools → Network tab
5. Search for something (e.g., "AI expert")
6. Verify request goes to `ese-backend-61as.onrender.com/api/v1/search` (not localhost)
7. Check search results load correctly

## Current Status

✅ **Everything is working!**
- Both services deployed and live
- Frontend connecting to production backend
- Backend health check passing
- CORS configured correctly
- Database connected with pgvector

## Questions Answered

**Q: Can I still run this locally?**
A: Yes! Two options:
1. `cd frontend && npm run dev` - connects to production backend
2. Create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` and run both frontend and backend locally

**Q: What if I need to change the backend URL?**
A: Update the hardcoded value in `frontend/src/lib/api.ts` line 3 and the CORS in `backend/app/main.py`

**Q: How do I save this chat?**
A: This file! `CHAT_HISTORY.md` contains everything we did.

## Contact & Resources

- GitHub Repo: https://github.com/abm312/expert-suitability-engine
- Render Dashboard: https://dashboard.render.com
- See `DEPLOYMENT.md` for full technical details
