from __future__ import annotations

import argparse
import sys

from .brain.history import ConversationHistory
from .brain.ollama import OllamaClient, OllamaError
from .brain.persona import load_system_prompt
from .brain.session import ChatSession
from .config import ASSISTANT_NAME, CHAT_MODEL, MEMORY_DB, OLLAMA_URL, PLATFORM_NAME
from .doctor import print_doctor_report
from .memory import MemoryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prak")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show local PrakVerse status.")
    subparsers.add_parser("doctor", help="Report hardware, Ollama, and model status.")
    chat = subparsers.add_parser("chat", help="Chat with Priyumvada through Ollama.")
    chat.add_argument("--model", default=CHAT_MODEL)
    chat.add_argument("--max-turns", type=int, default=12)

    remember = subparsers.add_parser("remember", help="Store a local memory.")
    remember.add_argument("content")
    remember.add_argument("--source", default="manual")

    search = subparsers.add_parser("search", help="Search local memories.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = MemoryStore(MEMORY_DB)

    if args.command == "status":
        print(f"{PLATFORM_NAME} local core")
        print(f"Assistant: {ASSISTANT_NAME}")
        print(f"Memory database: {MEMORY_DB}")
        print(f"Memories: {store.count()}")
        print("Cloud APIs: disabled")
        return 0

    if args.command == "doctor":
        return print_doctor_report()

    if args.command == "chat":
        return run_chat(args.model, args.max_turns)

    if args.command == "remember":
        memory = store.add(args.content, args.source)
        print(f"Stored memory #{memory.memory_id} [{memory.source}]")
        return 0

    if args.command == "search":
        try:
            memories = store.search(args.query, args.limit)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        if not memories:
            print("No matching local memories.")
            return 0
        for memory in memories:
            print(f"#{memory.memory_id} [{memory.source}] {memory.content}")
        return 0

    return 2


def run_chat(model: str, max_turns: int) -> int:
    session = ChatSession(
        OllamaClient(OLLAMA_URL, model),
        ConversationHistory(load_system_prompt(), max_turns),
    )
    print(f"{ASSISTANT_NAME} is ready. Type /exit to leave.")
    while True:
        try:
            user_content = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if user_content.lower() in {"/exit", "/quit", "exit", "quit"}:
            return 0
        if not user_content:
            continue
        try:
            print(f"{ASSISTANT_NAME}> ", end="", flush=True)
            chunks = []
            for chunk in session.client.stream_chat(session.history.messages(user_content)):
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            response = "".join(chunks)
            print()
            session.history.add_turn(user_content, response)
        except OllamaError as error:
            print(f"\nOllama error: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
