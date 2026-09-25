"""
CoachSphere Agent CLI
Run the agent from the terminal and see which tools it calls.

Usage (from the coachsphere/ folder):
    python -m agent.run
    python -m agent.run "Which team needs the most coaching attention and why?"
    python -m agent.run --stream "Who are the top performers in June 2024?"
"""

import sys
import argparse

# Default demo questions that exercise multi-tool chaining
DEMO_QUESTIONS = [
    "Which team needs the most coaching attention and why?",
    "Who are the top 3 performers in June 2024 and what is their quota attainment?",
    "Which skill improved the most across all reps, and which team leads in that skill?",
]


def run_once(question: str, stream: bool = False) -> None:
    from agent.graph import ask, stream as stream_fn

    print(f"\nQuestion: {question}")
    print("-" * 60)

    if stream:
        tool_calls = []
        answer_parts = []
        for event_type, content in stream_fn(question):
            if event_type == "tool_call":
                tool_calls.append(content)
                print(f"  [tool] {content}")
            elif event_type == "token":
                answer_parts.append(content)

        print("\nAnswer:")
        print("".join(answer_parts))
        if tool_calls:
            print(f"\n({len(tool_calls)} tool call(s): {', '.join(tool_calls)})")
    else:
        answer = ask(question)
        print("Answer:")
        print(answer)

    print("-" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="CoachSphere Agent CLI")
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="Question to ask the agent. Omit to run all demo questions.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the response and show which tools are called.",
    )
    args = parser.parse_args()

    if args.question:
        run_once(args.question, stream=args.stream)
    else:
        print("Running demo questions (--stream to see tool calls):\n")
        for q in DEMO_QUESTIONS:
            run_once(q, stream=args.stream)


if __name__ == "__main__":
    main()
