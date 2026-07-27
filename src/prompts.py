"""
Prompt builders. Kept separate from graph.py so the wording can be tuned
without touching orchestration logic.
"""

from typing import List

from src.models import AnswerFeedback, GeneratedQuestion, InterviewConfig, QARecord


def question_generation_prompt(
    config: InterviewConfig,
    difficulty,
    question_number: int,
    history: List[QARecord],
) -> str:
    asked_so_far = (
        "\n".join(f"- {qa.question.question}" for qa in history) or "None yet."
    )

    focus_line = f"\nExtra context from the candidate: {config.focus_notes}" if config.focus_notes else ""

    return f"""
You are an experienced technical/HR interviewer conducting a mock interview.

Candidate's target role: {config.role}
Interview type: {config.interview_type.value}
Current difficulty: {difficulty.value}
This is question #{question_number} of {config.num_questions}.{focus_line}

Questions already asked in this session (do NOT repeat these or ask something
too similar):
{asked_so_far}

Write ONE new interview question appropriate for the role, interview type,
and difficulty above. If the interview type is "Mixed", vary the category
across technical, behavioral, and situational questions as the session goes on.
Keep the question realistic, specific, and answerable in 30-90 seconds of
spoken response. Do not include the answer or any hints in the question text.
""".strip()


def answer_evaluation_prompt(
    config: InterviewConfig,
    question: GeneratedQuestion,
    answer: str,
) -> str:
    return f"""
You are an experienced interviewer giving direct, constructive feedback to a
candidate interviewing for: {config.role} ({config.interview_type.value}).

Question asked ({question.difficulty.value} difficulty, category: {question.category}):
"{question.question}"

Candidate's answer:
"{answer}"

Evaluate the answer honestly. Do not inflate scores — a vague, incomplete, or
off-topic answer should score low. Consider:
- correctness_score: technical/factual accuracy and completeness
- clarity_score: how well-structured and easy to follow the answer is
- confidence_score: how confident and decisive the answer sounds (not just tone —
  consider hedging, filler, and whether they committed to a position)
- overall_score: your holistic judgment of the answer's interview quality

Give 2-4 concrete strengths and 2-4 concrete improvements, a one-line verdict,
and one specific tip on what a strong answer would have included.
""".strip()


def summary_prompt(config: InterviewConfig, history: List[QARecord]) -> str:
    transcript_lines = []
    for i, qa in enumerate(history, start=1):
        transcript_lines.append(
            f"Q{i} ({qa.question.difficulty.value}, {qa.question.category}): "
            f"{qa.question.question}\n"
            f"Answer: {qa.answer}\n"
            f"Score: {qa.feedback.overall_score}/100 — {qa.feedback.verdict}"
        )
    transcript = "\n\n".join(transcript_lines)

    return f"""
You are wrapping up a mock interview for the role: {config.role}
({config.interview_type.value}).

Full transcript with per-question scores:

{transcript}

Write a final performance summary for the candidate. Be honest and specific,
referencing patterns you noticed across multiple answers rather than just
repeating single-question feedback. Give an overall_score (0-100) that
reflects the whole session, a short readiness_verdict, 3-5 top_strengths,
3-5 priority_improvements ordered by importance, and a short closing_advice
paragraph (3-4 sentences) the candidate can act on before their real interview.
""".strip()
