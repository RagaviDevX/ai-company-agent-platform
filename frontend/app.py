import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.components.api import get_json

st.set_page_config(
    page_title="AI Company",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #22d3ee 140%);
        color: white;
        margin-bottom: 1.2rem;
    }
    .hero h1 { margin: 0 0 .4rem 0; font-size: 2rem; }
    .hero p { margin: 0; opacity: .92; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>AI Company</h1>
      <p>Multi-model agentic platform — 10 specialists, free APIs only, LangGraph + LiteLLM.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

health = get_json("/health") or {}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Status", health.get("status", "offline"))
c2.metric("Groq", "ready" if health.get("groq") else "key missing")
c3.metric("OpenRouter", "ready" if health.get("openrouter") else "key missing")
c4.metric("Hugging Face", "ready" if health.get("huggingface") else "key missing")

st.subheader("How a job runs")
st.markdown(
    """
1. **CEO Planner** (DeepSeek via OpenRouter) breaks the request into subtasks  
2. **Research** searches the web  
3. **Architect + Database + Coder** design and implement  
4. **QA + Reviewer** test and polish  
5. **Memory + RAG** persist facts and documents  
"""
)

st.info("Open **Chat** in the sidebar and try: *Build me a College Attendance AI System.*")
st.caption("Start backend: `uvicorn backend.api.main:app --reload --port 8000`")
