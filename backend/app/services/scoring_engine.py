from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from app.metrics import (
    CredibilityMetric,
    TopicAuthorityMetric,
    CommunicationMetric,
    FreshnessMetric,
    GrowthMetric,
    MetricResult,
)
from app.schemas.search import MetricType, MetricConfig


@dataclass
class ScoringResult:
    """Complete scoring result for a creator"""
    overall_score: float
    metric_scores: Dict[str, MetricResult]
    weights_applied: Dict[str, float]
    factors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "subscores": {
                name: result.score 
                for name, result in self.metric_scores.items()
            },
            "factors": self.factors,
            "weights": self.weights_applied,
            "detailed_scores": {
                name: {
                    "score": result.score,
                    "available": result.available,
                    "factors": result.factors,
                }
                for name, result in self.metric_scores.items()
            }
        }


class ScoringEngine:
    """
    Scoring Engine
    
    Combines all metric modules to produce a final expert suitability score.
    
    Algorithm:
    1. Identify active metrics (available && enabled)
    2. Normalize weights to sum to 1.0
    3. Compute weighted sum
    
    No metric ever "breaks" scoring - unavailable metrics are simply excluded.
    """
    
    def __init__(self):
        self.metrics = {
            MetricType.CREDIBILITY: CredibilityMetric(),
            MetricType.TOPIC_AUTHORITY: TopicAuthorityMetric(),
            MetricType.COMMUNICATION: CommunicationMetric(),
            MetricType.FRESHNESS: FreshnessMetric(),
            MetricType.GROWTH: GrowthMetric(),
        }
    
    async def score_creator(
        self,
        creator_data: Dict[str, Any],
        metric_configs: Dict[MetricType, MetricConfig],
        topic_embedding: Optional[List[float]] = None,
        topic_keywords: Optional[List[str]] = None,
        embedding_service = None,
    ) -> ScoringResult:
        """
        Score a creator based on configured metrics.
        
        Args:
            creator_data: Dictionary with creator info, videos, transcripts
            metric_configs: Configuration for each metric (enabled, weight)
            topic_embedding: Embedding of the topic query
            topic_keywords: Keywords for topic matching
            
        Returns:
            ScoringResult with overall score and breakdown
        """
        metric_results: Dict[str, MetricResult] = {}
        active_weights: Dict[str, float] = {}
        all_factors: List[str] = []
        
        # Compute each metric
        for metric_type, config in metric_configs.items():
            if not config.enabled:
                continue
            
            metric = self.metrics.get(metric_type)
            if not metric:
                continue
            
            # Check availability
            if not metric.available(creator_data):
                result = MetricResult(
                    score=0.0,
                    available=False,
                    factors=[f"{metric.name} not available for this creator"]
                )
            else:
                # Compute with extra params for topic authority
                if metric_type == MetricType.TOPIC_AUTHORITY:
                    result = await metric.compute(
                        creator_data,
                        topic_embedding=topic_embedding,
                        topic_keywords=topic_keywords,
                        embedding_service=embedding_service
                    )
                else:
                    result = await metric.compute(creator_data)
            
            metric_results[metric_type.value] = result
            
            # Only include in scoring if available
            if result.available:
                active_weights[metric_type.value] = config.weight
                all_factors.extend(result.factors[:2])  # Top 2 factors per metric
        
        # Normalize weights
        total_weight = sum(active_weights.values())
        if total_weight > 0:
            normalized_weights = {
                name: weight / total_weight 
                for name, weight in active_weights.items()
            }
        else:
            normalized_weights = {}
        
        # Calculate final score
        final_score = 0.0
        for name, weight in normalized_weights.items():
            result = metric_results.get(name)
            if result:
                final_score += result.score * weight
        
        return ScoringResult(
            overall_score=final_score,
            metric_scores=metric_results,
            weights_applied=normalized_weights,
            factors=all_factors
        )
    
    async def score_creators_batch(
        self,
        creators_data: List[Dict[str, Any]],
        metric_configs: Dict[MetricType, MetricConfig],
        topic_embedding: Optional[List[float]] = None,
        topic_keywords: Optional[List[str]] = None,
    ) -> List[ScoringResult]:
        """Score multiple creators"""
        results = []
        for creator_data in creators_data:
            result = await self.score_creator(
                creator_data,
                metric_configs,
                topic_embedding,
                topic_keywords
            )
            results.append(result)
        return results

