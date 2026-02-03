# Expert Suitability Engine - Deployment Guide

## Overview
This is a full-stack web application that helps identify and rank YouTube-based tech/AI experts for expert-network recruiting. The app runs queries that take 5-10 minutes to complete.

## Tech Stack
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: FastAPI (Python), SQLAlchemy, Alembic
- **Database**: PostgreSQL 15 with pgvector extension
- **APIs**: YouTube Data API, OpenAI API (embeddings)
- **Hosting**: Render (all services on free tier)

## Live URLs
- **Frontend**: https://ese-frontend-dk65.onrender.com
- **Backend**: https://ese-backend-61as.onrender.com
- **GitHub**: https://github.com/abm312/expert-suitability-engine

## Deployment Architecture

### Services on Render
1. **ese-db** - PostgreSQL 15 database with pgvector
2. **ese-backend** - FastAPI backend (Docker)
3. **ese-frontend** - Next.js frontend (Docker)

All services are configured via `render.yaml` (Infrastructure as Code).

## Key Issues Fixed During Deployment

### 1. Empty Public Folder in Frontend Dockerfile
**Problem**: Frontend Docker build failed because `public/` folder was empty.
**Fix**: Modified `frontend/Dockerfile` to create the directory instead of copying:
```dockerfile
RUN mkdir -p ./public && chown nextjs:nodejs ./public
```

### 2. Async Database Driver Mismatch
**Problem**: SQLAlchemy error - "The asyncio extension requires an async driver"
**Fix**: Modified `backend/app/db/database.py` to convert Render's `postgres://` URL to `postgresql+asyncpg://`

### 3. CORS Blocking Frontend
**Problem**: Backend CORS only allowed localhost, blocking production frontend.
**Fix**: Added production frontend URL to `backend/app/main.py`:
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ese-frontend-dk65.onrender.com",
]
```

### 4. Environment Variables Not Working in Docker Build
**Problem**: Next.js requires `NEXT_PUBLIC_*` vars at build time, but Docker doesn't receive them from Render.
**Solution**: Hardcoded production backend URL as fallback in `frontend/src/lib/api.ts`:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://ese-backend-61as.onrender.com/api/v1';
```

## ⚠️ CRITICAL: Hardcoded Backend URL

### Why is it hardcoded?
Render's Docker builds don't pass environment variables to the build process. Since Next.js bakes `NEXT_PUBLIC_*` vars into the JavaScript bundle at build time (not runtime), we had to hardcode the production backend URL as a fallback.

### Where is it hardcoded?
**File**: `frontend/src/lib/api.ts` (line 3)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://ese-backend-61as.onrender.com/api/v1';
```

### When do you need to change it?

#### 1. If Backend URL Changes
If you redeploy the backend and get a new Render URL (e.g., `ese-backend-xyz.onrender.com`):

1. Update `frontend/src/lib/api.ts`:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://NEW-BACKEND-URL.onrender.com/api/v1';
```

2. Update CORS in `backend/app/main.py` (if frontend URL also changed):
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://NEW-FRONTEND-URL.onrender.com",  # Update this
]
```

3. Commit and push:
```bash
git add .
git commit -m "Update backend URL"
git push origin main
```

4. Wait for Render to auto-deploy both services.

#### 2. If You Want to Use Environment Variables Properly
To fix this properly (use env vars instead of hardcoding):

1. Modify `frontend/Dockerfile` to accept build args:
```dockerfile
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Add these lines:
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build
```

2. Update `render.yaml` frontend service:
```yaml
- type: web
  name: ese-frontend
  runtime: docker
  dockerfilePath: ./frontend/Dockerfile
  dockerContext: ./frontend
  envVars:
    - key: NEXT_PUBLIC_API_URL
      value: https://ese-backend-61as.onrender.com/api/v1
```

3. Remove the hardcoded URL from `api.ts`:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
```

**Note**: This hasn't been tested yet. The hardcoded approach works fine for now.

### Testing After Changes
After updating the URL:
1. Wait for frontend to redeploy
2. Open https://ese-frontend-dk65.onrender.com
3. Open browser DevTools → Network tab
4. Search for something
5. Verify request goes to the correct backend URL (not localhost)

## Running Locally

### Option 1: Frontend Only (connects to production backend)
```bash
cd frontend
npm run dev
```
Open http://localhost:3000 - will use production backend.

### Option 2: Full Local Development
1. Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

2. Start backend:
```bash
cd backend
# Set up your .env file with local DATABASE_URL, API keys, etc.
python -m uvicorn app.main:app --reload
```

3. Start frontend:
```bash
cd frontend
npm run dev
```

## Environment Variables

### Backend (set in Render)
- `DATABASE_URL` - Auto-provided by Render from ese-db
- `YOUTUBE_API_KEY` - YouTube Data API key
- `OPENAI_API_KEY` - OpenAI API key
- `DEBUG` - Set to `false` in production

### Frontend (set in Render)
- `NEXT_PUBLIC_API_URL` - Backend API URL (note: currently hardcoded as fallback)

## Deployment Workflow

1. Make changes locally
2. Test locally (optional)
3. Commit and push to GitHub:
```bash
git add .
git commit -m "Your changes"
git push origin main
```
4. Render auto-detects the push and redeploys affected services
5. Wait 2-5 minutes for deployment to complete

## Important Notes

- **Free Tier Limits**: Services sleep after 15 minutes of inactivity. First request after sleep takes ~30 seconds to wake up.
- **Request Timeouts**: Free tier has 15-minute timeout, which is enough for 5-10 minute queries.
- **Security**: Never commit `.env` files or API keys to GitHub. They're in `.gitignore`.
- **Database Migrations**: Backend automatically runs `alembic upgrade head` on startup.

## Troubleshooting

### Frontend shows "Cannot connect to server"
- Check if backend is awake (visit `/api/v1/health`)
- Check browser DevTools Network tab - should hit `ese-backend-61as.onrender.com`, not `localhost:8000`
- If still hitting localhost, verify the hardcoded URL in `frontend/src/lib/api.ts`

### Backend errors
- Check Render logs for the backend service
- Verify environment variables are set in Render dashboard
- Common issue: DATABASE_URL not properly formatted (should be `postgresql+asyncpg://`)

### CORS errors
- Verify frontend URL is in `backend/app/main.py` allowed origins list
- Check that the request is coming from the correct origin

## Future Improvements
- Implement proper environment variable handling for Docker builds (use build args)
- Set up CI/CD with automated testing
- Add monitoring/alerting for production issues
- Consider upgrading to paid tier for better performance
