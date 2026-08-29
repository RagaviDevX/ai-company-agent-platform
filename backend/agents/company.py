from backend.agents.base import run_agent
from backend.tools.search import format_search, web_search


def plan_task(task: str, rag_context: str, memories: str) -> str:
    payload = f"TASK:\n{task}\n\nMEMORIES:\n{memories or 'none'}\n\nRAG CONTEXT:\n{rag_context or 'none'}"
    return run_agent("planner", "planner_prompt.txt", payload)


def research_task(task: str) -> str:
    try:
        results = format_search(web_search(task))
    except Exception as exc:
        results = f"Search unavailable: {exc}"
    return run_agent("reasoning", "research_prompt.txt", f"TASK:\n{task}\n\nSEARCH:\n{results}")


def architect_task(task: str, plan: str, research: str) -> str:
    return run_agent(
        "reasoning",
        "architect_prompt.txt",
        f"TASK:\n{task}\n\nPLAN:\n{plan}\n\nRESEARCH:\n{research}",
    )


def code_task(task: str, architecture: str, schema: str) -> str:
    return run_agent(
        "coder",
        "coder_prompt.txt",
        f"TASK:\n{task}\n\nARCHITECTURE:\n{architecture}\n\nSCHEMA:\n{schema}",
    )


def database_task(task: str, architecture: str) -> str:
    return run_agent("planner", "database_prompt.txt", f"TASK:\n{task}\n\nARCHITECTURE:\n{architecture}")


def rag_answer(task: str, context: str) -> str:
    return run_agent("reasoning", "rag_prompt.txt", f"QUESTION:\n{task}\n\nDOCUMENTS:\n{context or 'none'}")


def qa_task(code: str, schema: str) -> str:
    return run_agent("planner", "qa_prompt.txt", f"CODE:\n{code}\n\nSCHEMA:\n{schema}")


def review_task(parts: dict[str, str]) -> str:
    blob = "\n\n".join(f"## {k}\n{v}" for k, v in parts.items() if v)
    return run_agent("reasoning", "review_prompt.txt", blob)


def extract_memories(task: str, final: str) -> str:
    return run_agent("reasoning", "memory_prompt.txt", f"USER:\n{task}\n\nOUTPUT:\n{final[:3000]}")
