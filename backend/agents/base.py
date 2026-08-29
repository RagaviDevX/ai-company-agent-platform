from backend.models.llm import chat
from backend.utils.paths import load_prompt


def run_agent(role: str, prompt_file: str, user_content: str) -> str:
    system = load_prompt(prompt_file)
    return chat(
        role,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    )
