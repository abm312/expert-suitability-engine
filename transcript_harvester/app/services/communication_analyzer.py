from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from app.schemas import (
    CommunicationAnalysisResponse,
    CommunicationVideoAnalysis,
    FillerWordStat,
    TranscriptDumpResponse,
)


class CommunicationAnalyzer:
    FILLER_PATTERNS: dict[str, str] = {
        "um": r"\bum+\b",
        "uh": r"\buh+\b",
        "like": r"\blike\b",
        "you know": r"\byou know\b",
        "basically": r"\bbasically\b",
        "actually": r"\bactually\b",
        "kind of": r"\bkind of\b",
        "sort of": r"\bsort of\b",
        "i mean": r"\bi mean\b",
        "literally": r"\bliterally\b",
        "honestly": r"\bhonestly\b",
    }

    def __init__(self) -> None:
        self._compiled_patterns = {
            term: re.compile(pattern, re.IGNORECASE)
            for term, pattern in self.FILLER_PATTERNS.items()
        }

    def analyze_dump(self, dump: TranscriptDumpResponse) -> CommunicationAnalysisResponse:
        video_analyses: list[CommunicationVideoAnalysis] = []
        aggregate_words = 0
        aggregate_sentences = 0
        aggregate_fillers = 0
        aggregate_filler_terms: Counter[str] = Counter()
        transcripts_analyzed = 0

        for video in dump.videos:
            analysis = self._analyze_video(video)
            video_analyses.append(analysis)

            if video.transcript_status == "fetched" and video.transcript_text:
                transcripts_analyzed += 1
                aggregate_words += analysis.word_count
                aggregate_sentences += analysis.sentence_count
                aggregate_fillers += analysis.filler_word_count
                for item in analysis.top_filler_words:
                    aggregate_filler_terms[item.term] += item.count

        average_sentence_length = (
            aggregate_words / aggregate_sentences if aggregate_sentences else 0.0
        )
        filler_word_ratio = (
            aggregate_fillers / aggregate_words if aggregate_words else 0.0
        )

        return CommunicationAnalysisResponse(
            channel_id=dump.channel_id,
            channel_name=dump.channel_name,
            analyzed_at=datetime.utcnow(),
            total_videos_considered=len(dump.videos),
            transcripts_analyzed=transcripts_analyzed,
            total_word_count=aggregate_words,
            total_sentence_count=aggregate_sentences,
            average_sentence_length=round(average_sentence_length, 2),
            filler_word_count=aggregate_fillers,
            filler_word_ratio=round(filler_word_ratio, 4),
            top_filler_words=self._counter_to_stats(aggregate_filler_terms),
            summary=self._build_summary(
                transcripts_analyzed=transcripts_analyzed,
                total_word_count=aggregate_words,
                filler_word_ratio=filler_word_ratio,
                average_sentence_length=average_sentence_length,
            ),
            videos=video_analyses,
        )

    def _analyze_video(self, video) -> CommunicationVideoAnalysis:
        if video.transcript_status != "fetched" or not video.transcript_text:
            return CommunicationVideoAnalysis(
                video_id=video.video_id,
                title=video.title,
                transcript_status=video.transcript_status,
            )

        word_count = self._count_words(video.transcript_text)
        sentence_count = self._count_sentences(video.transcript_text, video.segments)
        filler_counter = self._count_fillers(video.transcript_text)
        filler_word_count = sum(filler_counter.values())
        average_sentence_length = word_count / sentence_count if sentence_count else 0.0
        filler_word_ratio = filler_word_count / word_count if word_count else 0.0

        return CommunicationVideoAnalysis(
            video_id=video.video_id,
            title=video.title,
            transcript_status=video.transcript_status,
            word_count=word_count,
            sentence_count=sentence_count,
            average_sentence_length=round(average_sentence_length, 2),
            filler_word_count=filler_word_count,
            filler_word_ratio=round(filler_word_ratio, 4),
            top_filler_words=self._counter_to_stats(filler_counter),
        )

    def _count_words(self, text: str) -> int:
        return len(re.findall(r"\b[\w']+\b", text))

    def _count_sentences(self, text: str, segments: list) -> int:
        sentence_candidates = [
            candidate.strip()
            for candidate in re.split(r"[.!?]+", text)
            if self._count_words(candidate) >= 3
        ]
        if sentence_candidates:
            return len(sentence_candidates)

        # Fallback for transcripts with weak punctuation.
        segment_candidates = [
            (segment.text or "").strip()
            for segment in segments
            if self._count_words((segment.text or "").strip()) >= 3
        ]
        return len(segment_candidates)

    def _count_fillers(self, text: str) -> Counter[str]:
        counter: Counter[str] = Counter()
        for term, pattern in self._compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                counter[term] = len(matches)
        return counter

    def _counter_to_stats(self, counter: Counter[str]) -> list[FillerWordStat]:
        return [
            FillerWordStat(term=term, count=count)
            for term, count in counter.most_common(5)
        ]

    def _build_summary(
        self,
        transcripts_analyzed: int,
        total_word_count: int,
        filler_word_ratio: float,
        average_sentence_length: float,
    ) -> str:
        if transcripts_analyzed == 0:
            return "No transcript text was available to analyze."

        if total_word_count < 50:
            return "Available transcript text is too short for a stable communication read."

        if filler_word_ratio <= 0.01 and 6 <= average_sentence_length <= 20:
            return "Available transcripts suggest clear, concise communication."
        if filler_word_ratio <= 0.025 and 6 <= average_sentence_length <= 24:
            return "Available transcripts suggest generally clear communication with some filler usage."
        if average_sentence_length > 24:
            return "Available transcripts suggest longer-form explanations with denser phrasing."
        return "Available transcripts suggest a more conversational delivery style."
