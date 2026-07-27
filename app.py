"""
AI Interview Coach — Streamlit frontend.

Run with:  streamlit run app.py
"""

import json

import streamlit as st

from src.config import api_key_configured, settings
from src.gemini_client import GeminiNotConfiguredError
from src.graph import interview_graph
from src.models import InterviewConfig, InterviewType, DifficultyLevel

st.set_page_config(page_title=settings.APP_TITLE, page_icon="🎤", layout="centered")


# --------------------------------------------------------------------------
# Session state helpers
# --------------------------------------------------------------------------

def _init_session_state():
    st.session_state.setdefault("interview_state", None)
    st.session_state.setdefault("started", False)


def _run_graph(state: dict) -> dict | None:
    """Invoke the graph and surface friendly errors instead of a stack trace."""
    try:
        return interview_graph.invoke(state)
    except GeminiNotConfiguredError as e:
        st.error(str(e))
    except Exception as e:  # noqa: BLE001 - surfacing any API error to the user
        st.error(f"Something went wrong talking to Gemini: {e}")
    return None


def _reset():
    st.session_state.interview_state = None
    st.session_state.started = False


# --------------------------------------------------------------------------
# Sidebar — setup form
# --------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.header("Session setup")

        if not api_key_configured():
            st.warning(
                "No GEMINI_API_KEY found. Add one to a `.env` file "
                "(see `.env`) before starting a session.",
                icon="⚠️",
            )

        role = st.text_input("Target role", placeholder="e.g. Backend Engineer")
        interview_type = st.selectbox(
            "Interview type",
            options=list(InterviewType),
            format_func=lambda x: x.value,
        )
        difficulty = st.selectbox(
            "Starting difficulty",
            options=list(DifficultyLevel),
            format_func=lambda x: x.value,
            index=1,
        )
        num_questions = st.slider("Number of questions", min_value=3, max_value=12, value=5)
        focus_notes = st.text_area(
            "Extra context (optional)",
            placeholder="e.g. focus on Python + system design, 3 YOE",
        )

        start_disabled = not role.strip() or not api_key_configured()
        if st.button("Start interview", type="primary", disabled=start_disabled, use_container_width=True):
            config = InterviewConfig(
                role=role.strip(),
                interview_type=interview_type,
                difficulty=difficulty,
                num_questions=num_questions,
                focus_notes=focus_notes.strip() or None,
            )
            initial_state = {
                "config": config,
                "history": [],
                "current_question": None,
                "pending_answer": None,
                "current_difficulty": config.difficulty,
                "question_number": 0,
                "is_complete": False,
                "summary": None,
            }
            with st.spinner("Preparing your first question..."):
                result = _run_graph(initial_state)
            if result is not None:
                st.session_state.interview_state = result
                st.session_state.started = True
                st.rerun()

        if st.session_state.get("started"):
            st.divider()
            if st.button("Restart session", use_container_width=True):
                _reset()
                st.rerun()


# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------

def render_welcome():
    st.title("🎤 AI Interview Coach")
    st.write(
        "Configure a mock interview in the sidebar, then practice answering "
        "questions with structured, honest feedback after each one — plus a "
        "final readiness report at the end."
    )
    st.markdown(
        "- Questions adapt in difficulty based on how you're doing\n"
        "- Every answer gets scored on correctness, clarity, and confidence\n"
        "- You'll get a downloadable summary at the end"
    )


def render_feedback(feedback, expanded: bool = True):
    with st.container(border=True):
        cols = st.columns(4)
        cols[0].metric("Overall", f"{feedback.overall_score}/100")
        cols[1].metric("Correctness", f"{feedback.correctness_score}/100")
        cols[2].metric("Clarity", f"{feedback.clarity_score}/100")
        cols[3].metric("Confidence", f"{feedback.confidence_score}/100")

        st.caption(feedback.verdict)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Strengths**")
            for s in feedback.strengths:
                st.markdown(f"- {s}")
        with col_b:
            st.markdown("**Improve**")
            for i in feedback.improvements:
                st.markdown(f"- {i}")

        st.info(f"💡 {feedback.model_answer_tip}")


def render_transcript(history):
    for qa in history:
        with st.chat_message("assistant"):
            st.markdown(f"**[{qa.question.difficulty.value} · {qa.question.category}]**")
            st.write(qa.question.question)
        with st.chat_message("user"):
            st.write(qa.answer)
        render_feedback(qa.feedback)


def render_active_session(state: dict):
    config: InterviewConfig = state["config"]
    total = config.num_questions
    done = len(state.get("history", []))

    st.progress(min(done / total, 1.0), text=f"Question {min(done + 1, total)} of {total}")

    render_transcript(state.get("history", []))

    question = state.get("current_question")
    if question is not None:
        with st.chat_message("assistant"):
            st.markdown(f"**[{question.difficulty.value} · {question.category}]**")
            st.write(question.question)

        answer = st.chat_input("Type your answer...")
        if answer:
            state["pending_answer"] = answer
            with st.spinner("Evaluating your answer..."):
                result = _run_graph(state)
            if result is not None:
                st.session_state.interview_state = result
                st.rerun()


def render_summary(state: dict):
    summary = state["summary"]
    config: InterviewConfig = state["config"]

    st.success("Interview complete!")
    st.metric("Overall readiness score", f"{summary.overall_score}/100")
    st.subheader(summary.readiness_verdict)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Top strengths**")
        for s in summary.top_strengths:
            st.markdown(f"- {s}")
    with col_b:
        st.markdown("**Priority improvements**")
        for i in summary.priority_improvements:
            st.markdown(f"- {i}")

    st.markdown("**Closing advice**")
    st.write(summary.closing_advice)

    with st.expander("Full transcript"):
        render_transcript(state.get("history", []))

    export = {
        "role": config.role,
        "interview_type": config.interview_type.value,
        "summary": summary.model_dump(),
        "history": [qa.model_dump() for qa in state.get("history", [])],
    }
    st.download_button(
        "Download session as JSON",
        data=json.dumps(export, indent=2),
        file_name="interview_session.json",
        mime="application/json",
        use_container_width=True,
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    _init_session_state()
    render_sidebar()

    if not st.session_state.started or st.session_state.interview_state is None:
        render_welcome()
        return

    state = st.session_state.interview_state
    if state.get("is_complete"):
        render_summary(state)
    else:
        render_active_session(state)


if __name__ == "__main__":
    main()
