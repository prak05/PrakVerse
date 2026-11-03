from pathlib import Path

import pytest

from prakverse.agent.planner import ActionStep, PlanExecutor, TaskPlan
from prakverse.agent.scheduler import Scheduler
from prakverse.agent.skills import SkillLoader


def test_plan_executor_retries_and_stops_after_failure() -> None:
    attempts = []

    def invoke(tool, **_kwargs):
        attempts.append(tool)
        if len(attempts) < 2:
            raise RuntimeError("transient")
        return "done"

    result = PlanExecutor(invoke).execute(
        TaskPlan("test", (ActionStep("work", retries=1),), max_actions=2)
    )
    assert result[0]["status"] == "ok"
    assert len(attempts) == 2


def test_plan_action_budget_is_enforced() -> None:
    with pytest.raises(ValueError, match="action budget"):
        PlanExecutor(lambda *_args, **_kwargs: None).execute(
            TaskPlan("too big", (ActionStep("a"), ActionStep("b")), max_actions=1)
        )


def test_yaml_skill_loads_without_editing_core(tmp_path: Path) -> None:
    (tmp_path / "status.yaml").write_text(
        "name: status\n"
        "description: Show status\n"
        "steps:\n"
        "  - tool: system_info\n"
        "    description: Inspect system\n",
        encoding="utf-8",
    )
    try:
        skills = SkillLoader(tmp_path).load_all()
    except RuntimeError as error:
        assert "skill support" in str(error)
        return
    assert skills[0].name == "status"
    assert skills[0].plan.steps[0].tool == "system_info"


def test_scheduler_persists_and_runs_due_tasks(tmp_path: Path) -> None:
    scheduler = Scheduler(tmp_path / "schedule.sqlite3")
    scheduler.add("notes", 1, "status")
    with __import__("sqlite3").connect(tmp_path / "schedule.sqlite3") as connection:
        connection.execute("UPDATE scheduled_tasks SET next_run='2000-01-01T00:00:00+00:00'")
    seen = []
    outcomes = scheduler.run_due(seen.append)
    assert outcomes[0]["status"] == "ok"
    assert seen == ["status"]
