from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .planner import ActionStep, TaskPlan


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    plan: TaskPlan
    source: Path


class SkillLoader:
    """Loads YAML/JSON plans and Python skill modules from a directory."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> list[Skill]:
        skills = []
        for path in sorted(self.directory.iterdir()):
            if path.suffix.lower() in {".yaml", ".yml", ".json"}:
                skills.append(self._load_data(path))
            elif path.suffix.lower() == ".py":
                skill = self._load_python(path)
                if skill:
                    skills.append(skill)
        return skills

    def _load_data(self, path: Path) -> Skill:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            try:
                import yaml
            except ImportError as error:
                raise RuntimeError("Install skill support with: pip install -e '.[skills]'") from error
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return self._from_data(data, path)

    def _load_python(self, path: Path) -> Skill | None:
        spec = importlib.util.spec_from_file_location(f"prakverse_skill_{path.stem}", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        factory = getattr(module, "skill", None)
        return factory() if callable(factory) else None

    def _from_data(self, data: dict[str, Any], source: Path) -> Skill:
        steps = tuple(
            ActionStep(
                tool=item["tool"],
                arguments=item.get("arguments", {}),
                description=item.get("description", ""),
                retries=int(item.get("retries", 0)),
            )
            for item in data.get("steps", [])
        )
        return Skill(
            name=data["name"],
            description=data.get("description", ""),
            plan=TaskPlan(data.get("goal", data["name"]), steps, int(data.get("max_actions", 20))),
            source=source,
        )
