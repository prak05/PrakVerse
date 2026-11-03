from __future__ import annotations

import argparse
import sys

from .config import ASSISTANT_NAME, MEMORY_DB, PLATFORM_NAME
from .doctor import print_doctor_report
from .memory import MemoryStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prak")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show local PrakVerse status.")
    subparsers.add_parser("doctor", help="Report hardware, Ollama, and model status.")

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


if __name__ == "__main__":
    raise SystemExit(main())
