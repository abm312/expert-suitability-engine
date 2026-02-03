from typing import Any, Dict, List
import re
from statistics import mean, stdev
from app.metrics.base import BaseMetric, MetricResult


class CommunicationMetric(BaseMetric):
    """
    Communication Quality Module
    
    Analyzes transcript text to measure communication effectiveness.
    
    Signals:
    - Sentence length variance (consistent = better)
    - Filler word density (fewer = better)
    - Structural markers (headings, transitions = better)
    - Explanation language (teaching indicators)
    
    Output:
    - communication_score ∈ [0,1]
    
    Note: If no transcript available, module returns unavailable.
    """
    
    name = "communication"
    description = "Measures communication quality from transcript analysis"
    
    # Common filler words/phrases
    FILLER_WORDS = [
        "um", "uh", "like", "you know", "basically", "actually",
        "sort of", "kind of", "i mean", "right", "okay so",
        "literally", "honestly", "to be honest", "at the end of the day"
    ]
    
    # Structural/transition markers indicating organized content
    STRUCTURE_MARKERS = [
        "first", "second", "third", "finally", "lastly",
        "next", "then", "now", "moving on", "let's look at",
        "in summary", "to summarize", "in conclusion",
        "the key point", "importantly", "note that",
        "step one", "step two", "step 1", "step 2",
        "on one hand", "on the other hand", "however",
        "for example", "for instance", "such as",
        "let me explain", "here's how", "here's why"
    ]
    
    # Teaching/explanation indicators
    EXPLANATION_MARKERS = [
        "let me explain", "what this means", "in other words",
        "think of it as", "imagine", "picture this",
        "the reason is", "because", "this is important because",
        "you might wonder", "you might be thinking",
        "to understand", "to clarify", "simply put",
        "breaking it down", "let's break this down",
        "the idea here", "the concept", "fundamentally"
    ]
    
    def available(self, creator_data: Dict[str, Any]) -> bool:
        """Communication metric requires transcript data"""
        videos = creator_data.get("videos", [])
        for video in videos:
            transcript = video.get("transcript", {})
            if transcript and transcript.get("text"):
                return True
        return False
    
    async def compute(self, creator_data: Dict[str, Any], **kwargs) -> MetricResult:
        if not self.available(creator_data):
            return MetricResult(
                score=0.0,
                available=False,
                factors=["No transcripts available for communication analysis"]
            )
        
        # Gather all transcript text
        all_text = []
        for video in creator_data.get("videos", []):
            transcript = video.get("transcript", {})
            if transcript and transcript.get("text"):
                all_text.append(transcript["text"])
        
        if not all_text:
            return MetricResult(
                score=0.0,
                available=False,
                factors=["No transcript text found"]
            )
        
        combined_text = " ".join(all_text)
        
        factors = []
        scores = []
        
        # 1. Sentence structure score
        sentence_score, sentence_factor = self._analyze_sentence_structure(combined_text)
        scores.append(sentence_score * 0.25)
        factors.append(sentence_factor)
        
        # 2. Filler word density
        filler_score, filler_factor = self._analyze_filler_density(combined_text)
        scores.append(filler_score * 0.25)
        factors.append(filler_factor)
        
        # 3. Structural organization
        structure_score, structure_factor = self._analyze_structure(combined_text)
        scores.append(structure_score * 0.25)
        factors.append(structure_factor)
        
        # 4. Explanation quality
        explanation_score, explanation_factor = self._analyze_explanation_language(combined_text)
        scores.append(explanation_score * 0.25)
        factors.append(explanation_factor)
        
        total_score = sum(scores)
        
        return MetricResult(
            score=total_score,
            available=True,
            factors=factors,
            raw_data={
                "sentence_score": sentence_score,
                "filler_score": filler_score,
                "structure_score": structure_score,
                "explanation_score": explanation_score,
                "transcripts_analyzed": len(all_text),
                "total_words": len(combined_text.split())
            }
        )
    
    def _analyze_sentence_structure(self, text: str) -> tuple[float, str]:
        """Analyze sentence length consistency and readability"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(sentences) < 5:
            return 0.5, "Too few sentences for structure analysis"
        
        # Calculate word counts per sentence
        word_counts = [len(s.split()) for s in sentences]
        avg_length = mean(word_counts)
        
        if len(word_counts) > 1:
            length_std = stdev(word_counts)
        else:
            length_std = 0
        
        # Ideal: 15-25 words per sentence, low variance
        # Score based on being close to ideal range
        if 15 <= avg_length <= 25:
            length_score = 1.0
        elif 10 <= avg_length <= 30:
            length_score = 0.7
        else:
            length_score = 0.4
        
        # Variance penalty (high variance = inconsistent)
        variance_penalty = min(0.3, length_std / 30)
        
        score = max(0, length_score - variance_penalty)
        
        if score >= 0.7:
            factor = f"Clear sentence structure (avg {avg_length:.0f} words)"
        elif score >= 0.4:
            factor = f"Moderate sentence clarity (avg {avg_length:.0f} words)"
        else:
            factor = f"Variable sentence structure (avg {avg_length:.0f} words)"
        
        return score, factor
    
    def _analyze_filler_density(self, text: str) -> tuple[float, str]:
        """Count filler words relative to total words"""
        text_lower = text.lower()
        word_count = len(text.split())
        
        if word_count < 100:
            return 0.5, "Insufficient text for filler analysis"
        
        filler_count = 0
        for filler in self.FILLER_WORDS:
            filler_count += text_lower.count(filler)
        
        # Calculate density per 100 words
        filler_density = (filler_count / word_count) * 100
        
        # Score: 0 fillers = 1.0, 5+ per 100 words = 0
        if filler_density < 1:
            score = 1.0
            factor = "Minimal filler words - polished delivery"
        elif filler_density < 2:
            score = 0.8
            factor = "Low filler usage - good verbal clarity"
        elif filler_density < 3:
            score = 0.6
            factor = "Moderate filler usage"
        elif filler_density < 5:
            score = 0.4
            factor = "Higher filler word usage"
        else:
            score = 0.2
            factor = "Frequent filler words detected"
        
        return score, factor
    
    def _analyze_structure(self, text: str) -> tuple[float, str]:
        """Detect structural markers indicating organized content"""
        text_lower = text.lower()
        word_count = len(text.split())
        
        if word_count < 100:
            return 0.5, "Insufficient text for structure analysis"
        
        structure_count = 0
        markers_found = []
        
        for marker in self.STRUCTURE_MARKERS:
            count = text_lower.count(marker)
            if count > 0:
                structure_count += count
                markers_found.append(marker)
        
        # Density per 1000 words
        structure_density = (structure_count / word_count) * 1000
        
        if structure_density > 10:
            score = 1.0
            factor = "Well-organized with clear structure"
        elif structure_density > 5:
            score = 0.7
            factor = "Good content organization"
        elif structure_density > 2:
            score = 0.5
            factor = "Some structural elements present"
        else:
            score = 0.3
            factor = "Limited structural markers"
        
        return score, factor
    
    def _analyze_explanation_language(self, text: str) -> tuple[float, str]:
        """Detect teaching/explanation patterns"""
        text_lower = text.lower()
        word_count = len(text.split())
        
        if word_count < 100:
            return 0.5, "Insufficient text for explanation analysis"
        
        explanation_count = 0
        
        for marker in self.EXPLANATION_MARKERS:
            explanation_count += text_lower.count(marker)
        
        # Density per 1000 words
        explanation_density = (explanation_count / word_count) * 1000
        
        if explanation_density > 8:
            score = 1.0
            factor = "Strong teaching/explanation style"
        elif explanation_density > 4:
            score = 0.75
            factor = "Good explanatory approach"
        elif explanation_density > 2:
            score = 0.5
            factor = "Some explanatory content"
        else:
            score = 0.3
            factor = "Limited explanation patterns"
        
        return score, factor

