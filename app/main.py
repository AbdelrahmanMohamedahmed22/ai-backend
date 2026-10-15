from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(
    title="Agent Platform Backend",
    description=(
        "FastAPI backend for project, agent-version, run-state management, "
        "AgentSpec validation, and compiler integration."
    ),
    version="0.2.0",
)


class ItemCreate(BaseModel):
    """Payload used to create a legacy example item."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class Item(ItemCreate):
    id: int


class CompilerTarget(StrEnum):
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentSpec(BaseModel):
    """Validated contract consumed by platform compilers."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1_000)
    runtime: Literal["python", "node", "container"] = "python"
    entrypoint: str = Field(min_length=1, max_length=200)
    tools: list[str] = Field(default_factory=list, max_length=50)
    environment: dict[str, str] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class AgentSpecValidation(BaseModel):
    valid: Literal[True] = True
    normalized_spec: AgentSpec


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1_000)


class Project(ProjectCreate):
    id: str
    created_at: datetime


class AgentVersionCreate(BaseModel):
    agent_spec: AgentSpec
    commit_message: str = Field(default="Initial agent version", max_length=200)


class AgentVersion(AgentVersionCreate):
    id: str
    project_id: str
    version: int
    created_at: datetime


class RunCreate(BaseModel):
    version_id: str
    compiler: CompilerTarget
    input: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    status: Literal[RunStatus.SUCCEEDED, RunStatus.FAILED]
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=2_000)


class Run(BaseModel):
    id: str
    project_id: str
    version_id: str
    compiler: CompilerTarget
    status: RunStatus
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


projects: dict[str, Project] = {}
versions: dict[str, AgentVersion] = {}
runs: dict[str, Run] = {}
items: list[Item] = []


def now() -> datetime:
    return datetime.now(timezone.utc)


def get_project_or_404(project_id: str) -> Project:
    project = projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_version_or_404(version_id: str) -> AgentVersion:
    version = versions.get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Agent version not found")
    return version


@app.get("/", tags=["default"])
def read_root() -> dict[str, str]:
    return {"message": "Agent Platform Backend is running"}


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/info", tags=["service"])
def service_info() -> dict[str, str]:
    return {"name": "Agent Platform Backend", "version": app.version}


@app.post("/api/v1/agent-spec/validate", response_model=AgentSpecValidation, tags=["agent-spec"])
def validate_agent_spec(spec: AgentSpec) -> AgentSpecValidation:
    """Validate and return the normalized AgentSpec before compilation."""
    return AgentSpecValidation(normalized_spec=spec)


@app.post("/api/v1/projects", response_model=Project, status_code=201, tags=["projects"])
def create_project(payload: ProjectCreate) -> Project:
    project = Project(id=str(uuid4()), created_at=now(), **payload.model_dump())
    projects[project.id] = project
    return project


@app.get("/api/v1/projects", response_model=list[Project], tags=["projects"])
def list_projects() -> list[Project]:
    return list(projects.values())


@app.get("/api/v1/projects/{project_id}", response_model=Project, tags=["projects"])
def get_project(project_id: str) -> Project:
    return get_project_or_404(project_id)


@app.post(
    "/api/v1/projects/{project_id}/versions",
    response_model=AgentVersion,
    status_code=201,
    tags=["agent-versions"],
)
def create_agent_version(project_id: str, payload: AgentVersionCreate) -> AgentVersion:
    get_project_or_404(project_id)
    project_versions = [v for v in versions.values() if v.project_id == project_id]
    version = AgentVersion(
        id=str(uuid4()),
        project_id=project_id,
        version=len(project_versions) + 1,
        created_at=now(),
        **payload.model_dump(),
    )
    versions[version.id] = version
    return version


@app.get(
    "/api/v1/projects/{project_id}/versions",
    response_model=list[AgentVersion],
    tags=["agent-versions"],
)
def list_agent_versions(project_id: str) -> list[AgentVersion]:
    get_project_or_404(project_id)
    return [v for v in versions.values() if v.project_id == project_id]


@app.post("/api/v1/runs", response_model=Run, status_code=201, tags=["runs"])
def create_run(payload: RunCreate) -> Run:
    version = get_version_or_404(payload.version_id)
    run = Run(
        id=str(uuid4()),
        project_id=version.project_id,
        status=RunStatus.QUEUED,
        created_at=now(),
        updated_at=now(),
        **payload.model_dump(),
    )
    runs[run.id] = run
    return run


@app.get("/api/v1/runs/{run_id}", response_model=Run, tags=["runs"])
def get_run(run_id: str) -> Run:
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/api/v1/runs/{run_id}/result", response_model=Run, tags=["runs"])
def process_run_result(run_id: str, payload: RunResult) -> Run:
    """Accept a compiler result and move the run to a terminal state."""
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
        raise HTTPException(status_code=409, detail="Run is already complete")
    run.status = payload.status
    run.output = payload.output
    run.error = payload.error
    run.updated_at = now()
    return run


@app.get("/api/v1/items", response_model=list[Item], tags=["legacy-items"])
def list_items() -> list[Item]:
    return items


@app.post("/api/v1/items", response_model=Item, status_code=201, tags=["legacy-items"])
def create_item(payload: ItemCreate) -> Item:
    item = Item(id=len(items) + 1, **payload.model_dump())
    items.append(item)
    return item


@app.get("/api/v1/items/{item_id}", response_model=Item, tags=["legacy-items"])
def get_item(item_id: int) -> Item:
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")
