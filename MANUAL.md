# Expert Suitability Engine - Manual Setup Guide

## Prerequisites Check

Before starting, make sure you have:
- ✅ PostgreSQL 17 running (with pgvector extension)
- ✅ Python 3.9+ installed
- ✅ Node.js 20+ installed
- ✅ YouTube API key
- ✅ OpenAI API key

---

## Step 1: Start PostgreSQL

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# If not running, start it:
brew services start postgresql@17

# Verify it's running:
psql -d ese_db -c "SELECT version();"
```

**Expected output:** PostgreSQL version info

---

## Step 2: Verify Database Setup

```bash
# Connect to your database
psql -d ese_db

# Inside psql, check if pgvector extension exists:
\dx

# If you see "vector" in the list, you're good. Exit:
\q
```

**If pgvector is NOT installed:**
```bash
psql -d ese_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Step 3: Backend Setup

### 3.1 Navigate to Backend Directory

```bash
cd /Users/abdullahbinmasood/Documents/expert/backend
```

### 3.2 Activate Virtual Environment

```bash
source venv/bin/activate
```

**You should see `(venv)` in your terminal prompt.**

### 3.3 Create .env File

```bash
# Create .env file in backend directory
cat > .env << 'EOF'
YOUTUBE_API_KEY=your_youtube_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql+asyncpg://abdullahbinmasood@localhost:5432/ese_db
DATABASE_SYNC_URL=postgresql://abdullahbinmasood@localhost:5432/ese_db
EOF
```

### 3.4 Verify Dependencies

```bash
# Check if all packages are installed
pip list | grep -E "fastapi|uvicorn|sqlalchemy|openai|asyncpg"

# If missing packages, install:
pip install -r requirements.txt
```

### 3.5 Run Database Migrations

```bash
# Make sure you're in backend directory with venv activated
alembic upgrade head
```

**Expected output:** `INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial_schema`

### 3.6 Start Backend Server

```bash
# Make sure venv is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**✅ Backend is running!** Keep this terminal open.

---

## Step 4: Frontend Setup

### 4.1 Open a NEW Terminal Window

**Keep the backend terminal running!** Open a new terminal window/tab.

### 4.2 Navigate to Frontend Directory

```bash
cd /Users/abdullahbinmasood/Documents/expert/frontend
```

### 4.3 Verify Node.js Path

```bash
# Make sure Node.js is in PATH
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"

# Verify Node.js version
node --version
# Should show: v20.x.x or higher

# Verify npm
npm --version
```

### 4.4 Install Dependencies (if needed)

```bash
# Only run if node_modules doesn't exist or is incomplete
npm install
```

### 4.5 Start Frontend Server

```bash
npm run dev
```

**Expected output:**
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Ready in 2.3s
```

**✅ Frontend is running!**

---

## Step 5: Verify Everything Works

### 5.1 Test Backend

In a **third terminal window**, run:

```bash
curl http://localhost:8000/
```

**Expected output:** `{"message":"Expert Suitability Engine API"}`

### 5.2 Test Frontend

Open your browser and go to:
```
http://localhost:3000
```

You should see the search interface.

### 5.3 Test Full Flow

1. Type a search query: `"machine learning expert"`
2. Click "Search"
3. Wait for results (may take 2-4 minutes)
4. You should see creator cards with scores

---

## Troubleshooting

### Backend won't start

**Error: `Address already in use`**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
# Then restart backend
```

**Error: `ModuleNotFoundError`**
```bash
# Make sure venv is activated
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

**Error: `Database connection failed`**
```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Check database exists
psql -l | grep ese_db

# If missing, create it:
createdb ese_db
psql -d ese_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Frontend won't start

**Error: `Port 3000 already in use`**
```bash
# Kill Next.js process
pkill -f "next"
# Then restart frontend
```

**Error: `Command not found: npm`**
```bash
# Add Node.js to PATH
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
# Add to ~/.zshrc to make permanent:
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zshrc
```

### Search returns no results

1. Check backend logs for API errors
2. Verify API keys in `.env` file are correct
3. Check YouTube API quota (may be exhausted)
4. Check OpenAI API key is valid

---

## Quick Start Commands (Copy-Paste)

**Terminal 1 - Backend:**
```bash
cd /Users/abdullahbinmasood/Documents/expert/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd /Users/abdullahbinmasood/Documents/expert/frontend
export PATH="/opt/homebrew/opt/node@20/bin:$PATH"
npm run dev
```

---

## Stopping the Services

**To stop backend:**
- Press `Ctrl+C` in the backend terminal

**To stop frontend:**
- Press `Ctrl+C` in the frontend terminal

**To stop PostgreSQL:**
```bash
brew services stop postgresql@17
```

---

## File Locations

- **Backend code:** `/Users/abdullahbinmasood/Documents/expert/backend/app/`
- **Frontend code:** `/Users/abdullahbinmasood/Documents/expert/frontend/src/`
- **Backend .env:** `/Users/abdullahbinmasood/Documents/expert/backend/.env`
- **Database:** `ese_db` (PostgreSQL)

---

## Need Help?

Check the logs:
- **Backend logs:** Look at the terminal where `uvicorn` is running
- **Frontend logs:** Open browser DevTools (F12) → Console tab
- **Database logs:** `tail -f /opt/homebrew/var/log/postgresql@17.log`
