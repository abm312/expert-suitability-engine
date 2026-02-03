from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MetricResult:
    """Result from a metric computation"""
    score: float  # 0.0 to 1.0
    available: bool
    factors: List[str]  # Explanation factors
    raw_data: Dict[str, Any] = None  # Additional data for debugging/display
    
    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}
        # Clamp score to valid range
        self.score = max(0.0, min(1.0, self.score))


class BaseMetric(ABC):
    """Base class for all metric modules"""
    
    name: str = "base"
    description: str = "Base metric"
    
    @abstractmethod
    async def compute(self, creator_data: Dict[str, Any], **kwargs) -> MetricResult:
        """
        Compute the metric score for a creator.
        
        Args:
            creator_data: Dictionary containing creator info, videos, transcripts
            **kwargs: Additional parameters (e.g., topic embeddings)
            
        Returns:
            MetricResult with score (0-1), availability, and explanation factors
        """
        pass
    
    @abstractmethod
    def available(self, creator_data: Dict[str, Any]) -> bool:
        """
        Check if this metric can be computed for the given creator data.
        
        Args:
            creator_data: Dictionary containing creator info
            
        Returns:
            True if metric can be computed, False otherwise
        """
        pass
    
    def normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to 0-1 range"""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
    
    def sigmoid_normalize(self, value: float, midpoint: float, steepness: float = 1.0) -> float:
        """Sigmoid normalization for smooth scoring"""
        import math
        try:
            return 1 / (1 + math.exp(-steepness * (value - midpoint)))
        except OverflowError:
            return 1.0 if value > midpoint else 0.0

