# First Workroom Team Local Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first local Workroom team workflow that turns a business-hypothesis request into role-assigned work items through the existing Kernel-backed Workroom gateway.

**Architecture:** Add Workroom-owned team/workflow models, a deterministic local planner, and a small orchestrator that converts planned tasks into `WorkItemDraft` records. The slice stays local: GitHub Pages, Threads, promotion, QA, team management, and strategy are represented as planned work items, not external API calls.

**Tech Stack:** Python 3.11+, frozen dataclasses, `unittest`, existing `WorkroomKernelGateway`, external local `kernel` package dependency.

---

### Task 1: Workflow Models

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing tests**

Append these tests to `tests/test_models.py`:

```python
from agency_workroom.models import (
    TeamBlueprint,
    TeamRole,
    WorkflowPlan,
    WorkflowRequest,
    WorkflowTask,
)


class TeamWorkflowModelTests(unittest.TestCase):
    def test_team_blueprint_copies_roles(self) -> None:
        roles = [
            TeamRole(
                role_id="strategy_lead",
                display_name="Strategy Lead",
                responsibilities="Own positioning and next moves",
            )
        ]

        blueprint = TeamBlueprint(name="Validation Team", roles=roles)
        roles.append(
            TeamRole(
                role_id="qa_tester",
                display_name="QA Tester",
                responsibilities="Test artifacts",
            )
        )

        self.assertEqual("Validation Team", blueprint.name)
        self.assertEqual(1, len(blueprint.roles))
        self.assertEqual("strategy_lead", blueprint.roles[0].role_id)

    def test_workflow_request_payload_is_stable_and_metadata_is_copied(self) -> None:
        metadata = {"source": "founder-call"}
        request = WorkflowRequest(
            hypothesis="Founders will pay for an AI validation team",
            audience="early-stage SaaS founders",
            offer="48 hour landing page validation",
            constraints="No paid ads in the first pass",
            channels=("landing_page", "threads"),
            success_criteria="10 qualified waitlist signups",
            metadata=metadata,
        )
        metadata["source"] = "changed"

        self.assertEqual(
            request.to_payload(),
            {
                "hypothesis": "Founders will pay for an AI validation team",
                "audience": "early-stage SaaS founders",
                "offer": "48 hour landing page validation",
                "constraints": "No paid ads in the first pass",
                "channels": ["landing_page", "threads"],
                "success_criteria": "10 qualified waitlist signups",
                "metadata": {"source": "founder-call"},
            },
        )

    def test_workflow_request_rejects_blank_required_fields(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "hypothesis is required"):
            WorkflowRequest(
                hypothesis="",
                audience="founders",
                offer="validation",
                constraints="none",
                channels=("landing_page",),
                success_criteria="signups",
            )

    def test_workflow_task_converts_to_work_item_draft(self) -> None:
        task = WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Draft landing page",
            summary="Create the page structure and copy",
            priority="high",
            status="planned",
            metadata={"channel": "github_pages"},
        )

        draft = task.to_work_item_draft(department="validation_team")

        self.assertEqual("validation_team", draft.department)
        self.assertEqual("landing_builder", draft.agent_role)
        self.assertEqual("Draft landing page", draft.title)
        self.assertEqual("Create the page structure and copy", draft.summary)
        self.assertEqual("landing_page", draft.metadata["category"])
        self.assertEqual("planned", draft.metadata["status"])
        self.assertEqual("github_pages", draft.metadata["channel"])

    def test_workflow_plan_rejects_empty_tasks(self) -> None:
        request = WorkflowRequest(
            hypothesis="A",
            audience="B",
            offer="C",
            constraints="D",
            channels=("landing_page",),
            success_criteria="E",
        )

        with self.assertRaisesRegex(WorkroomModelError, "tasks are required"):
            WorkflowPlan(
                request=request,
                summary="Plan summary",
                tasks=(),
            )
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: FAIL with import errors for the new model classes.

**Step 3: Implement the models**

In `src/agency_workroom/models.py`, add these dataclasses after
`WorkroomModelError` helper functions and before `WorkItemDraft`:

```python
def _required_sequence(name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or not values:
        raise WorkroomModelError(f"{name} are required")
    cleaned = tuple(_required_text(name, value) for value in values)
    return cleaned


@dataclass(frozen=True)
class TeamRole:
    role_id: str
    display_name: str
    responsibilities: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "display_name", _required_text("display_name", self.display_name))
        object.__setattr__(
            self,
            "responsibilities",
            _required_text("responsibilities", self.responsibilities),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "role_id": self.role_id,
            "display_name": self.display_name,
            "responsibilities": self.responsibilities,
        }


@dataclass(frozen=True)
class TeamBlueprint:
    name: str
    roles: tuple[TeamRole, ...] | list[TeamRole]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        if not isinstance(self.roles, (tuple, list)) or not self.roles:
            raise WorkroomModelError("roles are required")
        if any(not isinstance(role, TeamRole) for role in self.roles):
            raise WorkroomModelError("roles must be TeamRole instances")
        object.__setattr__(self, "roles", tuple(self.roles))

    def role_ids(self) -> tuple[str, ...]:
        return tuple(role.role_id for role in self.roles)

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "roles": [role.to_payload() for role in self.roles],
        }


@dataclass(frozen=True)
class WorkflowRequest:
    hypothesis: str
    audience: str
    offer: str
    constraints: str
    channels: tuple[str, ...] | list[str]
    success_criteria: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "hypothesis", _required_text("hypothesis", self.hypothesis))
        object.__setattr__(self, "audience", _required_text("audience", self.audience))
        object.__setattr__(self, "offer", _required_text("offer", self.offer))
        object.__setattr__(self, "constraints", _required_text("constraints", self.constraints))
        object.__setattr__(self, "channels", _required_sequence("channels", self.channels))
        object.__setattr__(
            self,
            "success_criteria",
            _required_text("success_criteria", self.success_criteria),
        )
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "hypothesis": self.hypothesis,
            "audience": self.audience,
            "offer": self.offer,
            "constraints": self.constraints,
            "channels": list(self.channels),
            "success_criteria": self.success_criteria,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowTask:
    role_id: str
    category: str
    title: str
    summary: str
    priority: str = "normal"
    status: str = "planned"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        object.__setattr__(self, "priority", _required_text("priority", self.priority))
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
            "priority": self.priority,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    def to_work_item_draft(self, *, department: str) -> WorkItemDraft:
        metadata = {
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            **dict(self.metadata),
        }
        return WorkItemDraft(
            department=department,
            agent_role=self.role_id,
            title=self.title,
            summary=self.summary,
            metadata=metadata,
        )


@dataclass(frozen=True)
class WorkflowPlan:
    request: WorkflowRequest
    summary: str
    tasks: tuple[WorkflowTask, ...] | list[WorkflowTask]

    def __post_init__(self) -> None:
        if not isinstance(self.request, WorkflowRequest):
            raise WorkroomModelError("request must be a WorkflowRequest")
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        if not isinstance(self.tasks, (tuple, list)) or not self.tasks:
            raise WorkroomModelError("tasks are required")
        if any(not isinstance(task, WorkflowTask) for task in self.tasks):
            raise WorkroomModelError("tasks must be WorkflowTask instances")
        object.__setattr__(self, "tasks", tuple(self.tasks))

    def to_payload(self) -> dict[str, object]:
        return {
            "request": self.request.to_payload(),
            "summary": self.summary,
            "tasks": [task.to_payload() for task in self.tasks],
        }
```

Update `__all__` in `src/agency_workroom/models.py` and
`src/agency_workroom/__init__.py` to export:

```python
"TeamBlueprint",
"TeamRole",
"WorkflowPlan",
"WorkflowRequest",
"WorkflowTask",
```

**Step 4: Run the tests to verify they pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: add workroom team workflow models"
```

### Task 2: Default Team Blueprint

**Files:**
- Create: `src/agency_workroom/team.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_team.py`

**Step 1: Write the failing tests**

Create `tests/test_team.py`:

```python
from __future__ import annotations

import unittest

from agency_workroom.team import default_validation_team


class DefaultValidationTeamTests(unittest.TestCase):
    def test_default_team_contains_first_workroom_roles(self) -> None:
        team = default_validation_team()

        self.assertEqual("business_validation_team", team.name)
        self.assertEqual(
            (
                "hypothesis_researcher",
                "landing_builder",
                "qa_tester",
                "threads_operator",
                "growth_operator",
                "team_lead",
                "strategy_lead",
            ),
            team.role_ids(),
        )

    def test_default_team_returns_fresh_immutable_blueprint(self) -> None:
        first = default_validation_team()
        second = default_validation_team()

        self.assertIsNot(first, second)
        self.assertEqual(first.to_payload(), second.to_payload())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_team -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agency_workroom.team'`.

**Step 3: Implement the default team**

Create `src/agency_workroom/team.py`:

```python
from __future__ import annotations

from .models import TeamBlueprint, TeamRole


def default_validation_team() -> TeamBlueprint:
    return TeamBlueprint(
        name="business_validation_team",
        roles=(
            TeamRole(
                role_id="hypothesis_researcher",
                display_name="Hypothesis Researcher",
                responsibilities="Frame assumptions, risks, validation criteria, and customer discovery work.",
            ),
            TeamRole(
                role_id="landing_builder",
                display_name="Landing Builder",
                responsibilities="Plan landing-page copy, structure, assets, and publishing requirements.",
            ),
            TeamRole(
                role_id="qa_tester",
                display_name="QA Tester",
                responsibilities="Define acceptance checks for landing pages and workflow artifacts.",
            ),
            TeamRole(
                role_id="threads_operator",
                display_name="Threads Operator",
                responsibilities="Prepare Threads content, cadence, and response-handling tasks.",
            ),
            TeamRole(
                role_id="growth_operator",
                display_name="Growth Operator",
                responsibilities="Plan promotion channels, experiments, and metrics.",
            ),
            TeamRole(
                role_id="team_lead",
                display_name="Team Lead",
                responsibilities="Coordinate task ownership, sequencing, and blockers.",
            ),
            TeamRole(
                role_id="strategy_lead",
                display_name="Strategy Lead",
                responsibilities="Decide positioning, target segment, offer, and next strategic moves.",
            ),
        ),
    )


__all__ = [
    "default_validation_team",
]
```

Update `src/agency_workroom/__init__.py`:

```python
from .team import default_validation_team
```

and add `"default_validation_team"` to `__all__`.

**Step 4: Run the tests to verify they pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_team -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/team.py src/agency_workroom/__init__.py tests/test_team.py
git commit -m "feat: define default validation team"
```

### Task 3: Local Workflow Planner

**Files:**
- Create: `src/agency_workroom/planner.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_planner.py`

**Step 1: Write the failing tests**

Create `tests/test_planner.py`:

```python
from __future__ import annotations

import unittest

from agency_workroom.models import WorkflowRequest
from agency_workroom.planner import plan_business_validation_workflow
from agency_workroom.team import default_validation_team


class BusinessValidationPlannerTests(unittest.TestCase):
    def test_planner_creates_role_assigned_tasks_for_business_hypothesis(self) -> None:
        request = WorkflowRequest(
            hypothesis="Founders will pay for a 48 hour AI validation sprint",
            audience="early-stage SaaS founders",
            offer="landing page plus Threads validation",
            constraints="No paid ads and no external posting in the first pass",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="10 qualified waitlist signups",
            metadata={"request_id": "req_1"},
        )

        plan = plan_business_validation_workflow(
            request=request,
            team=default_validation_team(),
        )

        self.assertIn("48 hour AI validation sprint", plan.summary)
        self.assertEqual(8, len(plan.tasks))
        self.assertEqual(
            [
                "hypothesis_researcher",
                "strategy_lead",
                "landing_builder",
                "landing_builder",
                "qa_tester",
                "threads_operator",
                "growth_operator",
                "team_lead",
            ],
            [task.role_id for task in plan.tasks],
        )
        self.assertEqual(
            [
                "hypothesis_validation",
                "strategy",
                "landing_page",
                "github_pages",
                "testing",
                "threads",
                "promotion",
                "team_management",
            ],
            [task.category for task in plan.tasks],
        )
        self.assertTrue(all(task.status == "planned" for task in plan.tasks))

    def test_planner_rejects_missing_required_roles(self) -> None:
        team = default_validation_team()
        reduced_team = type(team)(name=team.name, roles=team.roles[:-1])
        request = WorkflowRequest(
            hypothesis="A",
            audience="B",
            offer="C",
            constraints="D",
            channels=("landing_page",),
            success_criteria="E",
        )

        with self.assertRaisesRegex(ValueError, "missing required roles"):
            plan_business_validation_workflow(request=request, team=reduced_team)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agency_workroom.planner'`.

**Step 3: Implement the planner**

Create `src/agency_workroom/planner.py`:

```python
from __future__ import annotations

from .models import TeamBlueprint, WorkflowPlan, WorkflowRequest, WorkflowTask

REQUIRED_VALIDATION_ROLES = (
    "hypothesis_researcher",
    "landing_builder",
    "qa_tester",
    "threads_operator",
    "growth_operator",
    "team_lead",
    "strategy_lead",
)


def plan_business_validation_workflow(
    *,
    request: WorkflowRequest,
    team: TeamBlueprint,
) -> WorkflowPlan:
    missing = [role_id for role_id in REQUIRED_VALIDATION_ROLES if role_id not in team.role_ids()]
    if missing:
        raise ValueError(f"missing required roles: {', '.join(missing)}")

    common_metadata = {
        "hypothesis": request.hypothesis,
        "audience": request.audience,
        "offer": request.offer,
        "constraints": request.constraints,
        "channels": list(request.channels),
        "success_criteria": request.success_criteria,
    }
    tasks = (
        WorkflowTask(
            role_id="hypothesis_researcher",
            category="hypothesis_validation",
            title="Frame validation assumptions",
            summary=(
                f"Turn the hypothesis '{request.hypothesis}' into assumptions, "
                f"risks, customer questions, and validation criteria for {request.audience}."
            ),
            priority="high",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="strategy_lead",
            category="strategy",
            title="Define validation strategy",
            summary=(
                f"Decide positioning, target segment, offer angle, and next moves for: {request.offer}."
            ),
            priority="high",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            summary=(
                "Draft the landing-page structure, core promise, sections, CTA, "
                "and copy needed to validate the offer."
            ),
            priority="high",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="landing_builder",
            category="github_pages",
            title="Plan GitHub Pages deployment",
            summary=(
                "Prepare the planned GitHub Pages deployment task. Do not deploy until "
                "a separate capability-backed deploy module is approved."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="qa_tester",
            category="testing",
            title="Define validation tests",
            summary=(
                "Define acceptance checks for the landing page, tracking links, "
                "copy consistency, and workflow artifacts."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="threads_operator",
            category="threads",
            title="Prepare Threads campaign",
            summary=(
                "Draft Threads posts, cadence, and response-handling plan. Do not post "
                "until a separate capability-backed Threads module is approved."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="growth_operator",
            category="promotion",
            title="Plan promotion experiments",
            summary=(
                "Identify low-risk promotion channels, messaging variants, and metrics "
                f"for the success criteria: {request.success_criteria}."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="team_lead",
            category="team_management",
            title="Coordinate validation sprint",
            summary=(
                "Sequence the work, track blockers, and prepare a final decision record "
                "for whether the hypothesis should continue."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
    )
    return WorkflowPlan(
        request=request,
        summary=f"Business validation workflow for hypothesis: {request.hypothesis}",
        tasks=tasks,
    )


__all__ = [
    "REQUIRED_VALIDATION_ROLES",
    "plan_business_validation_workflow",
]
```

Update `src/agency_workroom/__init__.py`:

```python
from .planner import REQUIRED_VALIDATION_ROLES, plan_business_validation_workflow
```

and add both names to `__all__`.

**Step 4: Run the tests to verify they pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/planner.py src/agency_workroom/__init__.py tests/test_planner.py
git commit -m "feat: plan business validation workflow"
```

### Task 4: Workflow Orchestrator

**Files:**
- Create: `src/agency_workroom/workflow.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_workflow.py`

**Step 1: Write the failing tests**

Create `tests/test_workflow.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom import WorkroomKernelGateway
from agency_workroom.models import WorkflowRequest
from agency_workroom.workflow import run_business_validation_workflow
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class BusinessValidationWorkflowTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_workflow_creates_planned_tasks_through_kernel_gateway(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        gateway = WorkroomKernelGateway.open(root / "kernel.jsonl", root / "workspace")
        request = WorkflowRequest(
            hypothesis="Founders will pay for private validation notes",
            audience="private founder segment",
            offer="private landing validation offer",
            constraints="private no paid ads constraint",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="private ten signups target",
            metadata={"private_request": "alpha"},
        )

        result = run_business_validation_workflow(
            gateway=gateway,
            declared_by_user_id="usr_workflow",
            request=request,
        )

        self.assertEqual("business_validation_team", result.team.name)
        self.assertEqual(8, len(result.plan.tasks))
        self.assertEqual(8, len(result.commits))
        self.assertTrue(all(commit.status == "success" for commit in result.commits))
        self.assertTrue(all(Path(commit.work_item_path).exists() for commit in result.commits))

    def test_workflow_does_not_put_raw_private_payloads_in_ledger(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        gateway = WorkroomKernelGateway.open(ledger_path, root / "workspace")
        request = WorkflowRequest(
            hypothesis="private hypothesis payload",
            audience="private audience payload",
            offer="private offer payload",
            constraints="private constraints payload",
            channels=("landing_page", "threads"),
            success_criteria="private success payload",
            metadata={"private_metadata": "private metadata payload"},
        )

        run_business_validation_workflow(
            gateway=gateway,
            declared_by_user_id="usr_workflow",
            request=request,
        )

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("private hypothesis payload", ledger_text)
        self.assertNotIn("private audience payload", ledger_text)
        self.assertNotIn("private offer payload", ledger_text)
        self.assertNotIn("private constraints payload", ledger_text)
        self.assertNotIn("private success payload", ledger_text)
        self.assertNotIn("private metadata payload", ledger_text)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workflow -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agency_workroom.workflow'`.

**Step 3: Implement the workflow orchestrator**

Create `src/agency_workroom/workflow.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from .kernel_gateway import WorkroomKernelGateway
from .models import TeamBlueprint, WorkItemCommit, WorkflowPlan, WorkflowRequest
from .planner import plan_business_validation_workflow
from .team import default_validation_team


@dataclass(frozen=True)
class BusinessValidationWorkflowResult:
    team: TeamBlueprint
    plan: WorkflowPlan
    commits: tuple[WorkItemCommit, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "team": self.team.to_payload(),
            "plan": self.plan.to_payload(),
            "commits": [commit.to_dict() for commit in self.commits],
        }


def run_business_validation_workflow(
    *,
    gateway: WorkroomKernelGateway,
    declared_by_user_id: str,
    request: WorkflowRequest,
) -> BusinessValidationWorkflowResult:
    team = default_validation_team()
    plan = plan_business_validation_workflow(request=request, team=team)
    commits = tuple(
        gateway.create_work_item(
            declared_by_user_id=declared_by_user_id,
            draft=task.to_work_item_draft(department=team.name),
        )
        for task in plan.tasks
    )
    return BusinessValidationWorkflowResult(
        team=team,
        plan=plan,
        commits=commits,
    )


__all__ = [
    "BusinessValidationWorkflowResult",
    "run_business_validation_workflow",
]
```

Update `src/agency_workroom/__init__.py`:

```python
from .workflow import BusinessValidationWorkflowResult, run_business_validation_workflow
```

and add both names to `__all__`.

**Step 4: Run the tests to verify they pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workflow -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/workflow.py src/agency_workroom/__init__.py tests/test_workflow.py
git commit -m "feat: run business validation workflow"
```

### Task 5: Integration And Boundary Verification

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Modify: `README.md`

**Step 1: Extend the integration test**

Add a second test to `tests/test_workroom_integration.py`:

```python
    def test_business_validation_workflow_uses_existing_kernel_authority_path(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
        request = WorkflowRequest(
            hypothesis="private workflow hypothesis",
            audience="private workflow audience",
            offer="private workflow offer",
            constraints="private workflow constraints",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="private workflow success criteria",
        )

        result = run_business_validation_workflow(
            gateway=gateway,
            declared_by_user_id="usr_integration",
            request=request,
        )

        self.assertEqual(8, len(result.commits))
        self.assertTrue(all(commit.work_item_ref.startswith("workroom-item://") for commit in result.commits))
        ledger = JsonlLedger(ledger_path)
        self.assertEqual(1 + (13 * 8), len(ledger.all()))
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertIn("workroom-item://", ledger_text)
        self.assertNotIn("private workflow hypothesis", ledger_text)
        self.assertNotIn("private workflow audience", ledger_text)
        self.assertNotIn("private workflow offer", ledger_text)
        self.assertNotIn("private workflow constraints", ledger_text)
        self.assertNotIn("private workflow success criteria", ledger_text)
```

Also update imports:

```python
from agency_workroom import WorkItemDraft, WorkroomKernelGateway
from agency_workroom.models import WorkflowRequest
from agency_workroom.workflow import run_business_validation_workflow
```

**Step 2: Run the integration test**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration -v
```

Expected: PASS.

**Step 3: Update README**

Add a short section after the current integration-path description:

```markdown
## First Validation Team

Workroom includes a local business-validation team workflow. It accepts a
structured hypothesis request and creates planned work items for hypothesis
research, strategy, landing-page work, GitHub Pages deployment planning, QA,
Threads operations, promotion, and team coordination.

The first slice is local. It does not deploy to GitHub Pages, post to Threads,
or run background agents. Those external effects require separate
capability-backed modules and current API/CLI verification before they are
added.
```

**Step 4: Run boundary checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess" src tests README.md docs || true
```

Expected: any matches are documentation, string literals, test fixtures, or task
category names. There must be no SDK imports, network calls, scheduler, or
runtime loop.

Run:

```bash
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: no output from Workroom implementation activity.

**Step 5: Commit**

```bash
git add tests/test_workroom_integration.py README.md
git commit -m "test: cover first validation team workflow"
```

### Task 6: Full Verification

**Files:**
- Modify only if verification finds a real issue.

**Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_team tests.test_planner tests.test_workflow tests.test_workroom_integration -v
```

Expected: PASS.

**Step 2: Run full suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: PASS.

If this environment flakes on temp directories, rerun with:

```bash
TMPDIR=/dev/shm PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

**Step 3: Run installed-package verification**

Run:

```bash
python -m venv /tmp/workroom-validation-team-venv
/tmp/workroom-validation-team-venv/bin/python -m pip install -e .
/tmp/workroom-validation-team-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 4: Check worktree and recent commits**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: clean Workroom tree and recent task commits visible.

**Step 5: Final commit only if fixes were needed**

If Step 1-4 required fixes, commit them:

```bash
git add <changed-files>
git commit -m "fix: stabilize validation team workflow"
```
