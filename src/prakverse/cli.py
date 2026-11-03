from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .brain.history import ConversationHistory
from .brain.ollama import OllamaClient, OllamaError
from .brain.persona import load_system_prompt
from .brain.session import ChatSession
from .config import (
    ASSISTANT_NAME,
    AUDIT_LOG,
    CHAT_MODEL,
    EMBED_MODEL,
    MEMORY_DB,
    MEMORY_DIR,
    OLLAMA_URL,
    PLATFORM_NAME,
)
from .doctor import print_doctor_report
from .memory import MemoryStore
from .knowledge import KnowledgeStore
from .agent.planner import ActionStep, PlanExecutor, TaskPlan
from .agent.scheduler import Scheduler
from .agent.skills import SkillLoader
from .config import SCHEDULE_DB, SKILLS_DIR
from .safety import SafetyPolicy
from .tools.audit import AuditLog
from .tools.local import register_local_tools
from .tools.registry import ToolContext, ToolRegistry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prak")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show local PrakVerse status.")
    subparsers.add_parser("doctor", help="Report hardware, Ollama, and model status.")
    chat = subparsers.add_parser("chat", help="Chat with Priyumvada through Ollama.")
    chat.add_argument("--model", default=CHAT_MODEL)
    chat.add_argument("--max-turns", type=int, default=12)
    listen = subparsers.add_parser("listen", help="Start the local voice loop.")
    listen.add_argument("--audio", type=Path, help="Transcribe one local audio file.")
    listen.add_argument("--no-speak", action="store_true")

    remember = subparsers.add_parser("remember", help="Store a local memory.")
    remember.add_argument("content")
    remember.add_argument("--source", default="manual")

    search = subparsers.add_parser("search", help="Search local memories.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    ingest = subparsers.add_parser("ingest", help="Index local documents.")
    ingest.add_argument("path", type=Path)
    recall = subparsers.add_parser("recall", help="Search indexed documents with citations.")
    recall.add_argument("query")
    recall.add_argument("--limit", type=int, default=5)
    memory = subparsers.add_parser("memory", help="Manage the local knowledge store.")
    memory_subparsers = memory.add_subparsers(dest="memory_command", required=True)
    export = memory_subparsers.add_parser("export")
    export.add_argument("path", type=Path)
    memory_subparsers.add_parser("wipe")
    fact = subparsers.add_parser("fact", help="Manage explicitly confirmed facts.")
    fact_subparsers = fact.add_subparsers(dest="fact_command", required=True)
    add_fact = fact_subparsers.add_parser("remember")
    add_fact.add_argument("content")
    add_fact.add_argument("--source", default="confirmed")
    fact_subparsers.add_parser("list")
    forget = fact_subparsers.add_parser("forget")
    forget.add_argument("id", type=int)
    plan = subparsers.add_parser("plan", help="Execute a bounded local action plan.")
    plan.add_argument("tool", nargs="+", help="Tool names to execute in order.")
    plan.add_argument("--max-actions", type=int, default=20)
    skill = subparsers.add_parser("skill", help="List or run local skills.")
    skill_subparsers = skill.add_subparsers(dest="skill_command", required=True)
    skill_subparsers.add_parser("list")
    skill_run = skill_subparsers.add_parser("run")
    skill_run.add_argument("name")
    schedule = subparsers.add_parser("schedule", help="Manage recurring local tasks.")
    schedule_subparsers = schedule.add_subparsers(dest="schedule_command", required=True)
    schedule_subparsers.add_parser("list")
    schedule_add = schedule_subparsers.add_parser("add")
    schedule_add.add_argument("name")
    schedule_add.add_argument("interval", type=int)
    schedule_add.add_argument("payload")
    schedule_subparsers.add_parser("run-due")
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
    if args.command == "listen":
        return run_listen(args.audio, not args.no_speak)
    if args.command == "plan":
        registry = build_tool_registry()
        steps = tuple(ActionStep(tool) for tool in args.tool)
        plan = TaskPlan("CLI action plan", steps, args.max_actions)
        print("Plan:")
        print("\n".join(plan.summary()))
        print_plan_results(PlanExecutor(registry.invoke).execute(plan))
        return 0
    if args.command == "skill":
        loader = SkillLoader(SKILLS_DIR)
        skills = loader.load_all()
        if args.skill_command == "list":
            for skill in skills:
                print(f"{skill.name}: {skill.description}")
            return 0
        selected = next((skill for skill in skills if skill.name == args.name), None)
        if selected is None:
            print(f"Skill not found: {args.name}", file=sys.stderr)
            return 1
        print("Plan:")
        print("\n".join(selected.plan.summary()))
        print_plan_results(PlanExecutor(build_tool_registry().invoke).execute(selected.plan))
        return 0
    if args.command == "schedule":
        scheduler = Scheduler(SCHEDULE_DB)
        if args.schedule_command == "list":
            for task in scheduler.list():
                print(f"#{task.task_id} {task.name} every {task.interval_seconds}s next={task.next_run}")
        elif args.schedule_command == "add":
            task = scheduler.add(args.name, args.interval, args.payload)
            print(f"Scheduled {task.name} for {task.next_run}")
        else:
            for outcome in scheduler.run_due(lambda payload: run_skill_payload(payload)):
                print(outcome)
        return 0

    knowledge = KnowledgeStore(
        MEMORY_DIR,
        embedder=OllamaClient(OLLAMA_URL, EMBED_MODEL),
    )
    if args.command == "ingest":
        print(knowledge.ingest(args.path))
        return 0
    if args.command == "recall":
        for result in knowledge.search(args.query, args.limit):
            print(
                f"[{result['source']}:{result['line_start']}-{result['line_end']}] "
                f"{result['content']}"
            )
        return 0
    if args.command == "memory":
        if args.memory_command == "export":
            knowledge.export(args.path)
            print(f"Exported knowledge to {args.path}")
        else:
            knowledge.wipe()
            print("Knowledge store wiped.")
        return 0
    if args.command == "fact":
        if args.fact_command == "remember":
            fact_id = knowledge.add_fact(args.content, args.source)
            print(f"Stored confirmed fact #{fact_id}")
        elif args.fact_command == "list":
            for item in knowledge.list_facts():
                print(f"#{item['id']} [{item['source']}] {item['content']}")
        else:
            print("Forgot fact." if knowledge.forget_fact(args.id) else "Fact not found.")
        return 0

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


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry(ToolContext(SafetyPolicy(), AuditLog(AUDIT_LOG)))
    register_local_tools(registry)
    return registry


def print_plan_results(results: list[dict[str, object]]) -> None:
    for result in results:
        print(
            f"Step {result['step']} [{result['status']}] {result['tool']}: "
            f"{result.get('result', result.get('error', ''))}"
        )


def run_skill_payload(payload: str) -> list[dict[str, object]]:
    skill = next(
        (item for item in SkillLoader(SKILLS_DIR).load_all() if item.name == payload),
        None,
    )
    if skill is None:
        raise ValueError(f"Skill not found: {payload}")
    return PlanExecutor(build_tool_registry().invoke).execute(skill.plan)


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


def run_listen(audio_path: Path | None, speak: bool) -> int:
    from .voice.pipeline import build_local_pipeline
    from .voice.speech import VoiceUnavailable

    try:
        pipeline = build_local_pipeline()
    except VoiceUnavailable as error:
        print(f"Voice unavailable: {error}", file=sys.stderr)
        print(
            "Push-to-talk fallback: use `prak chat` until local voice dependencies are installed."
        )
        return 1
    session = ChatSession(
        OllamaClient(OLLAMA_URL, CHAT_MODEL),
        ConversationHistory(load_system_prompt(), 12),
    )
    if audio_path is not None:
        try:
            response = pipeline.process_audio(audio_path, session.respond, speak=speak)
        except Exception as error:
            print(f"Voice error: {error}", file=sys.stderr)
            return 1
        if response:
            print(response)
        return 0
    print("Voice loop requires a microphone adapter; use --audio for push-to-talk files.")
    print("Wake word target: Hey Priyumvada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
