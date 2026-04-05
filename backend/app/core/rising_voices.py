from app.schemas.search import FilterConfig, MetricConfig, MetricType


RISING_VOICES_QUERIES = [
    "AI/ML Engineer",
    "LLM Expert",
    "Data Scientist",
    "MLOps Specialist",
    "Computer Vision",
]

RISING_VOICES_METRICS = {
    MetricType.CREDIBILITY: MetricConfig(enabled=True, weight=0.25),
    MetricType.TOPIC_AUTHORITY: MetricConfig(enabled=True, weight=0.30),
    MetricType.COMMUNICATION: MetricConfig(enabled=True, weight=0.15),
    MetricType.FRESHNESS: MetricConfig(enabled=True, weight=0.15),
    MetricType.GROWTH: MetricConfig(enabled=True, weight=0.15),
}

RISING_VOICES_FILTERS = FilterConfig(
    subscriber_min=10000,
    uploads_last_90_days_min=2,
)
