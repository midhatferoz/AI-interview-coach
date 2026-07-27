"""
LangGraph workflow for the interview session.

The graph is invoked once per "turn":
  - First call (no pending_answer yet): generates the opening question.
  - Every later call: the caller sets `pending_answer` to the candidate's
    latest answer before invoking. The graph evaluates that answer, adapts
    difficulty, and then either asks the next question or produces the
    final summary if the session is complete.

This keeps Streamlit's job simple: collect input, invoke(state), store the
returned state, re-render.
"""

from langgraph.graph import END, START, StateGraph

from src.gemini_client import generate_structured
from src.models import (
    AnswerFeedback,
    DifficultyLevel,
    GeneratedQuestion,
    InterviewState,
    QARecord,
    SessionSummary,
)
from src.prompts import (
    answer_evaluation_prompt,
    question_generation_prompt,
    summary_prompt,
)

SYSTEM_INSTRUCTION = (
    "You are a rigorous but encouraging mock interview coach. Always follow "
    "the requested JSON schema exactly and never include markdown formatting "
    "in your output."
)


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

def node_generate_question(state: InterviewState) -> dict:
    config = state["config"]
    difficulty = state.get("current_difficulty", config.difficulty)
    question_number = state.get("question_number", 0) + 1
    history = state.get("history", [])

    prompt = question_generation_prompt(config, difficulty, question_number, history)
    question = generate_structured(prompt, GeneratedQuestion, SYSTEM_INSTRUCTION)

    return {
        "current_question": question,
        "question_number": question_number,
        "current_difficulty": difficulty,
        "pending_answer": None,
    }


def node_evaluate_answer(state: InterviewState) -> dict:
    config = state["config"]
    question = state["current_question"]
    answer = state["pending_answer"]

    prompt = answer_evaluation_prompt(config, question, answer)
    feedback = generate_structured(prompt, AnswerFeedback, SYSTEM_INSTRUCTION)

    record = QARecord(question=question, answer=answer, feedback=feedback)
    history = state.get("history", []) + [record]

    new_difficulty = _adjust_difficulty(
        state.get("current_difficulty", config.difficulty), feedback.overall_score
    )

    return {
        "history": history,
        "current_difficulty": new_difficulty,
        "pending_answer": None,
        "current_question": None,
    }


def node_generate_summary(state: InterviewState) -> dict:
    config = state["config"]
    history = state.get("history", [])

    prompt = summary_prompt(config, history)
    summary = generate_structured(prompt, SessionSummary, SYSTEM_INSTRUCTION)

    return {"summary": summary, "is_complete": True, "current_question": None}


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

def _adjust_difficulty(current: DifficultyLevel, score: int) -> DifficultyLevel:
    """Simple adaptive difficulty: strong answers escalate, weak ones ease off."""
    if score >= 75:
        return DifficultyLevel.from_rank(current.rank + 1)
    if score <= 40:
        return DifficultyLevel.from_rank(current.rank - 1)
    return current


def route_entry(state: InterviewState) -> str:
    if state.get("pending_answer") is None:
        return "first_question"
    return "evaluate"


def route_after_evaluation(state: InterviewState) -> str:
    config = state["config"]
    if state.get("question_number", 0) >= config.num_questions:
        return "finish"
    return "continue"


# --------------------------------------------------------------------------
# Graph assembly
# --------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(InterviewState)

    graph.add_node("evaluate_answer", node_evaluate_answer)
    graph.add_node("generate_question", node_generate_question)
    graph.add_node("generate_summary", node_generate_summary)

    graph.add_conditional_edges(
        START,
        route_entry,
        {"first_question": "generate_question", "evaluate": "evaluate_answer"},
    )
    graph.add_conditional_edges(
        "evaluate_answer",
        route_after_evaluation,
        {"continue": "generate_question", "finish": "generate_summary"},
    )
    graph.add_edge("generate_question", END)
    graph.add_edge("generate_summary", END)

    return graph.compile()


# Compiled once and reused across calls.
interview_graph = build_graph()
