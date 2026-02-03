# Expert Suitability Engine (ESE)

Identify, rank, and explain YouTube-based tech/AI experts for expert-network recruiting using public data only.

![ESE Banner](https://via.placeholder.com/1200x400?text=Expert+Suitability+Engine)

## 🎯 What It Does

ESE helps you discover the perfect YouTube tech experts for consulting engagements by:

- **Discovering** creators via YouTube search
- **Scoring** them across 5 configurable metrics
- **Filtering** by hard constraints (subscribers, activity, etc.)
- **Explaining** why each expert is a good match

## 🏗️ Architecture

```
Frontend (Next.js 14)
       │
       ▼
Backend API (Python FastAPI)
       │
       ├── YouTube Data API (discovery & data)
       ├── OpenAI API (embeddings)
       └── PostgreSQL + pgvector (storage & similarity search)
```

## 📊 Metric Modules

Each metric is toggle-able and weighted:

| Metric | Description | Weight |
|--------|-------------|--------|
| **Credibility** | Channel age, content depth, external validation | 20% |
| **Topic Authority** | Alignment with target expertise (semantic) | 30% |
| **Communication** | Clarity, structure, teaching effectiveness | 20% |
| **Freshness** | Recent content and active publishing | 15% |
| **Growth** | Subscriber growth and audience momentum | 15% |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension
- YouTube Data API key
- OpenAI API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Set up database
createdb ese_db
psql ese_db -c "CREATE EXTENSION vector;"

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:3000` to use the app!

## 📁 Project Structure

```
expert/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Configuration
│   │   ├── db/            # Database models
│   │   ├── metrics/       # Scoring modules
│   │   │   ├── credibility.py
│   │   │   ├── topic_authority.py
│   │   │   ├── communication.py
│   │   │   ├── freshness.py
│   │   │   └── growth.py
│   │   ├── schemas/       # Pydantic models
│   │   └── services/      # Business logic
│   ├── alembic/           # Database migrations
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── app/           # Next.js pages
    │   ├── components/    # React components
    │   ├── lib/           # Utilities & API client
    │   └── types/         # TypeScript types
    └── package.json
```

## 🔌 API Endpoints

### Search & Discovery

```http
POST /api/v1/search
Content-Type: application/json

{
  "topic_query": "Large Language Model expert",
  "topic_keywords": ["LLM", "GPT", "transformer"],
  "metrics": {
    "credibility": { "enabled": true, "weight": 0.2 },
    "topic_authority": { "enabled": true, "weight": 0.3 },
    ...
  },
  "filters": {
    "subscriber_min": 50000,
    "subscriber_max": 250000
  }
}
```

### Response: Creator Card

```json
{
  "creators": [
    {
      "id": 1,
      "channel_name": "AI Expert",
      "overall_score": 0.847,
      "subscores": {
        "credibility": 0.82,
        "topic_authority": 0.91,
        ...
      },
      "why_expert": [
        "Highly credible with 3+ year channel history",
        "Strong alignment with 'LLM' topics",
        "Active GitHub presence"
      ],
      "suggested_topics": [
        "LLM fine-tuning strategies",
        "Production deployment considerations"
      ]
    }
  ]
}
```

## 🎛️ Configuration

### Filters (Hard Constraints)

- **Subscriber Range**: 50K - 250K (configurable)
- **Avg Video Length**: > 8 minutes
- **Growth Rate**: > X%
- **Recent Uploads**: In last 90 days
- **Topic Relevance**: > 0.5

### Metric Weights

Adjust weights via sliders. Weights are normalized across enabled metrics.

## 🔒 v1 Scope (STRICT)

### ✅ In Scope
- YouTube creators only
- Tech / AI content
- Public API data
- Scoring + filtering
- Explainability

### ❌ Out of Scope
- Outreach automation
- Payments
- Scheduling
- Transcript sales
- LinkedIn integration

## 🛣️ Future Extensions (Deferred)

- Podcasts
- Blogs
- GitHub deep analysis
- Outreach automation
- Compliance workflows

## 📄 License

MIT License - See LICENSE file for details.

---

Built with ❤️ for expert network recruiting

