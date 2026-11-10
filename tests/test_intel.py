import json
from pathlib import Path

from prakverse.intel import CentralIntel
from prakverse.knowledge import KnowledgeStore


def test_central_intel_syncs_named_projects(tmp_path: Path) -> None:
    project = tmp_path / "linkedin"
    project.mkdir()
    (project / "README.md").write_text(
        "LinkedIn Indo creates evidence-based career documents.", encoding="utf-8"
    )
    catalog = tmp_path / "intel.json"
    catalog.write_text(
        json.dumps(
            {
                "projects": [
                    {"name": "linkedin-indo", "path": str(project), "domain": "career"}
                ]
            }
        ),
        encoding="utf-8",
    )
    intel = CentralIntel(KnowledgeStore(tmp_path / "knowledge"), catalog)

    outcome = intel.sync()

    assert outcome[0]["name"] == "linkedin-indo"
    assert outcome[0]["status"] == "ok"
    assert intel.status()[0]["chunks"] == 1
    assert intel.knowledge.search("career documents")
