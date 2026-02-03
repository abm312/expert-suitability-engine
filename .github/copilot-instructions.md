# Expert Suitability Engine (ESE) - AI Coding Guidelines

## Architecture Overview

ESE is a full-stack application for discovering and ranking YouTube tech/AI experts:

- **Backend**: FastAPI (Python) with async SQLAlchemy, PostgreSQL + pgvector
- **Frontend**: Next.js 14 (TypeScript) with Tailwind CSS
- **External APIs**: YouTube Data API v3, OpenAI Embeddings
- **Deployment**: Docker Compose with health checks

### Core Data Flow
```
Search Request → CreatorService.search_creators()
    ↓
FilterService.apply_filters() → Filter by subscribers/videos/etc
    ↓
ScoringEngine.score_creator() → Compute 5 metrics in parallel
    ↓
ExplainabilityService.generate_explanations() → Natural language reasons
    ↓
Return CreatorCard[] with scores + explanations
```

## Key Patterns & Conventions

### Backend Services Architecture
- **CreatorService**: Main orchestrator, coordinates all other services
- **Modular Metrics**: Each metric (credibility, topic_authority, etc.) inherits from `BaseMetric`
- **Async Everywhere**: All database operations and API calls use `async/await`
- **Dependency Injection**: Services instantiated in `CreatorService.__init__()`

### Metric Implementation Pattern
```python
class ExampleMetric(BaseMetric):
    name = "example"
    description = "Brief description"
    
    def available(self, creator_data: Dict[str, Any]) -> bool:
        # Check if required data exists
        return creator_data.get("some_field") is not None
    
    async def compute(self, creator_data: Dict[str, Any], **kwargs) -> MetricResult:
        if not self.available(creator_data):
            return MetricResult(score=0.0, available=False, factors=[])
        
        # Compute score 0.0-1.0
        score = calculate_score(creator_data)
        
        # Return factors for explainability
        factors = ["Reason 1", "Reason 2"]
        
        return MetricResult(score=score, available=True, factors=factors)
```

### Database Patterns
- **Async SQLAlchemy**: Use `AsyncSession` for all queries
- **pgvector**: Store embeddings as `Vector(1536)` columns
- **Relationships**: Creator → Videos (cascade delete), Creator → MetricsSnapshots
- **Migrations**: Always use Alembic, never manual schema changes

### API Schema Patterns
- **Pydantic Models**: Strict validation with `Field` constraints
- **Enums**: Use `str, Enum` for metric types and other constants
- **Optional Fields**: Use `Optional[T]` with defaults in `Field()`
- **Nested Configs**: `Dict[MetricType, MetricConfig]` for flexible metric settings

## Critical Developer Workflows

### Local Development Setup
```bash
# Start all services
docker-compose up -d

# Backend: Run migrations then server
cd backend
alembic upgrade head
uvicorn app.main:app --reload

# Frontend: Install and dev server
cd frontend
npm install
npm run dev
```

### Database Operations
```bash
# Create migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current
```

### Testing API Endpoints
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Search request
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"topic_query": "machine learning", "topic_keywords": ["ML", "AI"]}'
```

## Common Implementation Patterns

### Adding a New Metric
1. Create `app/metrics/new_metric.py` inheriting from `BaseMetric`
2. Add to `app/services/scoring_engine.py` imports and metric list
3. Update `MetricType` enum in `app/schemas/search.py`
4. Add default config in `SearchRequest.metrics`
5. Update database migration if needed

### Frontend Component Structure
- **Hooks**: Business logic in `useSearch.ts`, API calls in `useApi.ts`
- **Components**: Pure UI in `/components/`, composed in `/app/`
- **Types**: Shared interfaces in `/types/index.ts`
- **API Client**: Centralized in `/lib/api.ts` with error handling

### Error Handling
- **Backend**: Use `HTTPException` for API errors, log details
- **Frontend**: `APIError` class with status codes, user-friendly messages
- **Validation**: Pydantic handles request validation automatically

## Key Files to Reference

- `backend/app/services/creator_service.py` - Main business logic flow
- `backend/app/metrics/base.py` - Metric interface and result structure  
- `backend/app/services/scoring_engine.py` - How metrics are combined
- `backend/app/schemas/search.py` - Request/response models
- `frontend/src/lib/api.ts` - API client patterns
- `docker-compose.yml` - Service dependencies and environment
- `backend/alembic/versions/` - Database schema evolution

## Environment & Dependencies

- **Python**: 3.11+, asyncpg for PostgreSQL, pgvector for embeddings
- **Node.js**: 18+, Next.js 14 with TypeScript
- **Database**: PostgreSQL 15+ with pgvector extension
- **APIs**: YouTube Data API key, OpenAI API key required
- **Dev Tools**: Alembic for migrations, ESLint for frontend linting

## Performance Considerations

- **Embeddings**: Cached in database, computed once per video
- **Metrics**: Computed in parallel when possible
- **Pagination**: Always implement limit/offset in API responses
- **Vector Search**: Use pgvector's cosine similarity for topic matching</content>
<parameter name="filePath">/Users/abdullahbinmasood/Documents/expert/.github/copilot-instructions.md