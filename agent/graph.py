"""
CoachSphere Agent Graph
LangGraph ReAct agent that uses Groq to answer questions about sales coaching analytics.

The agent decides which tools to call, chains multiple calls for complex questions,
and synthesises a final answer from the retrieved data.

Usage:
    from agent.graph import ask
    print(ask("Which team needs the most coaching attention and why?"))
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from agent.tools import ALL_TOOLS

# Load GROQ_API_KEY from coachsphere/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── LLM ────────────────────────────────────────────────────────────────────────
# llama-3.3-70b-versatile is fast, free-tier friendly, and handles tool calls well
_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)

# ── System prompt ───────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are CoachSphere's AI analytics assistant.

You have access to 6 months of sales coaching data (Jan-Jun 2024) across four teams:
Enterprise, SMB, EMEA, and APAC.

Rules:
- ALWAYS call a tool to retrieve data before answering. Never invent numbers.
- For multi-part questions, call multiple tools — one call per data need.
- Cite specific figures from the tool results in your final answer.
- Keep answers concise and actionable: what does the data say and what should the manager do?
- When comparing teams or identifying issues, show the actual numbers that support your conclusion.
- The data period is Jan-Jun 2024. If asked about other periods, say the data only covers that range.
"""

# ── Agent ───────────────────────────────────────────────────────────────────────
_agent = create_react_agent(
    model=_llm,
    tools=ALL_TOOLS,
    prompt=SYSTEM_PROMPT,
)


def ask(question: str) -> str:
    """
    Ask the CoachSphere agent a question and return its final answer.

    Args:
        question: Natural language question about sales coaching analytics.

    Returns:
        The agent's final text answer, grounded in data from the CoachSphere database.
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": question}]})
    # Last message is always the final AI response
    return result["messages"][-1].content


def stream(question: str):
    """
    Stream the agent's response token by token. Yields (event_type, content) tuples.

    Args:
        question: Natural language question.

    Yields:
        Tuples of ("tool_call", tool_name) when a tool is invoked,
        or ("token", text) for answer tokens.
    """
    for chunk in _agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="updates",
    ):
        for node, updates in chunk.items():
            for msg in updates.get("messages", []):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        yield "tool_call", tc["name"]
                elif hasattr(msg, "content") and isinstance(msg.content, str):
                    if node == "agent":
                        yield "token", msg.content
