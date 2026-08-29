from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.company import (
    architect_task,
    code_task,
    database_task,
    extract_memories,
    plan_task,
    qa_task,
    rag_answer,
    research_task,
    review_task,
)
from backend.config.settings import settings
from backend.memory.store import MemoryStore
from backend.rag.pipeline import RAGPipeline


class CompanyState(TypedDict, total=False):
    task: str
    user_id: int
    plan: str
    research: str
    architecture: str
    schema: str
    code: str
    rag_context: str
    rag_answer: str
    qa: str
    review: str
    memories_saved: str
    logs: list[str]
    final: str


def _log(state: CompanyState, name: str) -> list[str]:
    logs = list(state.get("logs") or [])
    logs.append(name)
    return logs


def node_rag(state: CompanyState) -> CompanyState:
    rag = RAGPipeline()
    context = rag.context_block(state["task"])
    answer = rag_answer(state["task"], context) if context else ""
    return {"rag_context": context, "rag_answer": answer, "logs": _log(state, "RAG")}


def node_plan(state: CompanyState) -> CompanyState:
    memory = MemoryStore()
    mems = memory.list_memories(state.get("user_id") or settings.default_user_id)
    mem_text = "\n".join(m["memory"] for m in mems[:20])
    plan = plan_task(state["task"], state.get("rag_context") or "", mem_text)
    return {"plan": plan, "logs": _log(state, "CEO Planner")}


def node_research(state: CompanyState) -> CompanyState:
    return {"research": research_task(state["task"]), "logs": _log(state, "Research")}


def node_architect(state: CompanyState) -> CompanyState:
    architecture = architect_task(state["task"], state.get("plan") or "", state.get("research") or "")
    return {"architecture": architecture, "logs": _log(state, "Architect")}


def node_database(state: CompanyState) -> CompanyState:
    schema = database_task(state["task"], state.get("architecture") or "")
    return {"schema": schema, "logs": _log(state, "Database")}


def node_coder(state: CompanyState) -> CompanyState:
    code = code_task(state["task"], state.get("architecture") or "", state.get("schema") or "")
    return {"code": code, "logs": _log(state, "Coder")}


def node_qa(state: CompanyState) -> CompanyState:
    qa = qa_task(state.get("code") or "", state.get("schema") or "")
    return {"qa": qa, "logs": _log(state, "QA")}


def node_review(state: CompanyState) -> CompanyState:
    review = review_task(
        {
            "plan": state.get("plan") or "",
            "research": state.get("research") or "",
            "architecture": state.get("architecture") or "",
            "schema": state.get("schema") or "",
            "code": state.get("code") or "",
            "rag": state.get("rag_answer") or "",
            "qa": state.get("qa") or "",
        }
    )
    return {"review": review, "final": review, "logs": _log(state, "Reviewer")}


def node_memory(state: CompanyState) -> CompanyState:
    user_id = state.get("user_id") or settings.default_user_id
    notes = extract_memories(state["task"], state.get("final") or "")
    store = MemoryStore()
    if notes and "API keys are not configured" not in notes:
        store.add_memory(user_id, notes)
    store.add_conversation(user_id, state["task"], state.get("final") or "")
    return {"memories_saved": notes, "logs": _log(state, "Memory")}


def build_graph():
    graph = StateGraph(CompanyState)
    graph.add_node("rag", node_rag)
    graph.add_node("plan", node_plan)
    graph.add_node("research", node_research)
    graph.add_node("architect", node_architect)
    graph.add_node("database", node_database)
    graph.add_node("coder", node_coder)
    graph.add_node("qa", node_qa)
    graph.add_node("review", node_review)
    graph.add_node("memory", node_memory)

    graph.add_edge(START, "rag")
    graph.add_edge("rag", "plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "architect")
    graph.add_edge("architect", "database")
    graph.add_edge("database", "coder")
    graph.add_edge("coder", "qa")
    graph.add_edge("qa", "review")
    graph.add_edge("review", "memory")
    graph.add_edge("memory", END)
    return graph.compile()


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP


def run_company(task: str, user_id: int | None = None) -> dict:
    result = get_app().invoke(
        {
            "task": task,
            "user_id": user_id or settings.default_user_id,
            "logs": [],
        }
    )
    return dict(result)
