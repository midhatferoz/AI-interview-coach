"""
Pydantic schemas used across the app.

Keeping every AI-facing data structure as a Pydantic model lets us ask
Gemini for structured JSON output (via response_schema) instead of parsing
free text, and it gives Streamlit clean, typed objects to render.
"""

from enum import Enum
from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class InterviewType(str, Enum):
    TECHNICAL = "Technical"
    HR_BEHAVIORAL = "HR / Behavioral"
    SYSTEM_DESIGN = "System Design"
    MIXED = "Mixed"


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

    @property
    def rank(self) -> int:
        return {"Easy": 0, "Medium": 1, "Hard": 2}[self.value]

    @classmethod
    def from_rank(cls, rank: int) -> "DifficultyLevel":
        rank = max(0, min(2, rank))
        return [cls.EASY, cls.MEDIUM, cls.HARD][rank]


# --------------------------------------------------------------------------
# Setup / configuration
# --------------------------------------------------------------------------

class InterviewConfig(BaseModel):
    """User-selected settings captured on the setup screen."""

    role: str = Field(..., description="Target job role, e.g. 'Backend Engineer'")
    interview_type: InterviewType
    difficulty: DifficultyLevel
    num_questions: int = Field(default=5, ge=3, le=15)
    focus_notes: Optional[str] = Field(
        default=None,
        description="Optional extra context from the user, e.g. specific tech stack",
    )


# --------------------------------------------------------------------------
# Structured Gemini outputs
# --------------------------------------------------------------------------

class GeneratedQuestion(BaseModel):
    """One interview question, produced by Gemini."""

    question: str = Field(..., description="The interview question text")
    category: str = Field(..., description="Short topic label, e.g. 'System Design'")
    difficulty: DifficultyLevel
    focus_area: str = Field(
        ..., description="What skill this question is really probing for"
    )


class AnswerFeedback(BaseModel):
    """Structured evaluation of a candidate's answer, produced by Gemini."""

    correctness_score: int = Field(..., ge=0, le=100)
    clarity_score: int = Field(..., ge=0, le=100)
    confidence_score: int = Field(..., ge=0, le=100)
    overall_score: int = Field(..., ge=0, le=100)
    verdict: str = Field(..., description="One short sentence summarizing the answer")
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    model_answer_tip: str = Field(
        ..., description="A concise tip on what a strong answer would include"
    )


class SessionSummary(BaseModel):
    """Final wrap-up report, produced by Gemini once the session ends."""

    overall_score: int = Field(..., ge=0, le=100)
    readiness_verdict: str = Field(
        ..., description="One-line verdict, e.g. 'Solid for mid-level roles'"
    )
    top_strengths: List[str] = Field(default_factory=list)
    priority_improvements: List[str] = Field(default_factory=list)
    closing_advice: str = Field(..., description="A short paragraph of closing advice")


# --------------------------------------------------------------------------
# Session bookkeeping (not sent to Gemini directly)
# --------------------------------------------------------------------------

class QARecord(BaseModel):
    """One completed question/answer/feedback turn, kept for history + export."""

    question: GeneratedQuestion
    answer: str
    feedback: AnswerFeedback


# --------------------------------------------------------------------------
# LangGraph state
# --------------------------------------------------------------------------

class InterviewState(TypedDict, total=False):
    """
    The single state object that flows through the LangGraph graph.

    total=False because different nodes only need to set a subset of keys;
    LangGraph merges partial dict returns into the running state.
    """

    config: InterviewConfig
    history: List[QARecord]
    current_question: Optional[GeneratedQuestion]
    pending_answer: Optional[str]
    current_difficulty: DifficultyLevel
    question_number: int
    is_complete: bool
    summary: Optional[SessionSummary]
