# Prompt for Claude — Agent Platform Backend

You are a senior backend engineer. Work on the existing FastAPI project in `D:\ai-backend`.

## Project goal

Build and maintain the backend service for an agent platform. The backend must provide:

- FastAPI endpoints and backend services.
- PostgreSQL data models and database migrations.
- Pydantic validation for `AgentSpec` before compilation.
- Project, agent-version, and run-state management.
- API, database, and integration tests.
- Clear API contracts and OpenAPI documentation.
- Integration boundaries for platform compilers such as Claude Code and Codex.
- Request/result processing for AI services and compiler jobs.

## Current project state

The project currently contains a FastAPI application in `main.py` with:

- `GET /`
- `GET /health`
- `GET /api/v1/info`
- Legacy example item endpoints under `/api/v1/items`.
- `POST /api/v1/agent-spec/validate`.
- Project endpoints under `/api/v1/projects`.
- Agent-version endpoints under `/api/v1/projects/{project_id}/versions`.
- Run endpoints under `/api/v1/runs`.
- `POST /api/v1/runs/{run_id}/result` for compiler result callbacks.

The current implementation stores data in memory. Treat it as a prototype that must be refactored into a maintainable production-oriented backend.

## Required domain model

Design PostgreSQL-backed models for:

1. `projects`
   - `id` UUID primary key
   - `name`
   - `description`
   - `created_at`
   - `updated_at`

2. `agent_versions`
   - `id` UUID primary key
   - `project_id` foreign key to projects
   - `version_number`
   - `agent_spec` JSONB
   - `commit_message`
   - `created_at`
   - Unique constraint on `(project_id, version_number)`

3. `runs`
   - `id` UUID primary key
   - `project_id` foreign key
   - `agent_version_id` foreign key
   - `compiler` enum/string: `claude_code` or `codex`
   - `status` enum/string: `queued`, `running`, `succeeded`, `failed`
   - `input_payload` JSONB
   - `output_payload` JSONB nullable
   - `error_message` nullable
   - `created_at`
   - `updated_at`

Add indexes for project lookups, version lookups, run status, and creation time.

## AgentSpec contract

Use Pydantic models with strict validation and reject unknown fields unless there is a documented reason to allow them.

The minimum AgentSpec fields are:

```json
{
  "name": "research-agent",
  "description": "Optional description",
  "runtime": "python",
  "entrypoint": "agents.research:run",
  "tools": ["web_search"],
  "environment": {},
  "config": {}
}
```

Allowed runtimes: `python`, `node`, `container`.

Validation must happen:

- When explicitly calling the validation endpoint.
- Before creating an agent version.
- Before dispatching a compiler run.

Return useful validation errors through standard FastAPI 422 responses.

## API contract

Keep these routes and improve them rather than breaking them:

- `GET /health`
- `GET /api/v1/info`
- `POST /api/v1/agent-spec/validate`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/versions`
- `GET /api/v1/projects/{project_id}/versions`
- `POST /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs/{run_id}/result`

Use response models for every endpoint. Use correct HTTP status codes:

- `201` for creation.
- `404` for missing projects, versions, or runs.
- `409` for invalid state transitions or duplicate versions.
- `422` for invalid request bodies.

## Compiler and AI-service integration

Create a clean adapter interface, for example:

```python
class CompilerAdapter(Protocol):
    async def submit(self, request: CompileRequest) -> CompileResponse: ...
```

Implement separate adapters or stubs for:

- `ClaudeCodeCompiler`
- `CodexCompiler`

The initial adapters may be deterministic mock implementations, but they must have clear interfaces so real connectors can be added later. Do not put provider-specific logic directly inside FastAPI route handlers.

Process compiler requests and results through service-layer functions. Keep request validation, persistence, compiler dispatch, and result persistence separate.

## Database and migrations

Use SQLAlchemy 2.x with PostgreSQL support and Alembic migrations. Read the database URL from an environment variable such as:

```text
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/agent_platform
```

Provide:

- A database session dependency.
- Transaction boundaries around writes.
- An initial migration for projects, agent_versions, and runs.
- A local development option that can use SQLite only for tests if necessary, while keeping PostgreSQL as the production target.

Never store secrets or API keys in source code.

## Testing requirements

Add tests for:

1. Health and service-info endpoints.
2. Valid AgentSpec validation.
3. Invalid AgentSpec rejection.
4. Project creation and retrieval.
5. Agent-version creation and sequential version numbers.
6. Missing project/version/run handling.
7. Run creation and state updates.
8. Duplicate or invalid terminal state transitions.
9. Compiler adapter integration using mocks.
10. Database repositories using an isolated test database.

Tests must be runnable with:

```powershell
pytest -q
```

## Engineering constraints

- Keep route handlers thin.
- Use typed Python code.
- Prefer async endpoints and async database sessions where appropriate.
- Keep business logic in services.
- Keep persistence logic in repositories.
- Avoid global mutable state in production code.
- Preserve backwards compatibility for the current public routes.
- Add useful docstrings and OpenAPI descriptions.
- Update `README.md` with setup, environment variables, migrations, tests, and API examples.
- Do not add authentication or billing behavior unless explicitly requested.
- Do not make external API calls during tests.

## Expected deliverables

Before finishing:

1. Refactor the project into a clear package structure.
2. Add PostgreSQL models and an initial Alembic migration.
3. Add service and repository layers.
4. Add compiler adapter interfaces and mock adapters.
5. Add API, database, and integration tests.
6. Update requirements and README.
7. Run formatting, type checks if configured, and `pytest -q`.
8. Report changed files, test results, migration commands, and any assumptions.

Start by inspecting the existing files. Do not delete working functionality without replacing it with an equivalent or better implementation.

## Product specification reference: AgentForge PDF

An attached product document is also part of the requirements:

```text
AgentForge_AI_System_for_Designing_Compiling_Evaluating_and_Optimizing_Coding_Agents_Registration (1).pdf
```

Treat that PDF as the product-level specification for **AgentForge**. Read it fully before making architectural decisions. Reconcile the PDF with the implementation requirements in this prompt; if there is a conflict, preserve the existing API compatibility and explicitly document the decision.

While analyzing the PDF, extract and convert the following into implementation artifacts:

1. **Product vision and actors**
   - Identify the users, operators, platform services, AI services, compiler providers, and evaluation components.
   - Explain the end-to-end lifecycle from agent design to compilation, execution, evaluation, optimization, and registration.

2. **Core domain objects**
   - Map every important object in the document to a typed Pydantic schema and, where persistent, a PostgreSQL table.
   - At minimum, relate the document concepts to projects, AgentSpecs, agent versions, compiler requests, runs, run results, evaluations, optimization iterations, and registrations.

3. **State machines and workflows**
   - Extract all statuses and transitions described or implied by the PDF.
   - Represent invalid transitions explicitly and return HTTP 409 where appropriate.
   - Keep long-running compiler, evaluation, and optimization operations asynchronous and observable through run/state endpoints.

4. **Compiler and AI integration**
   - Identify every external provider or compiler mentioned in the PDF.
   - Implement provider-neutral ports/adapters rather than coupling route handlers to a provider.
   - Define normalized request/result envelopes, correlation IDs, timeout handling, retries, and provider error mapping.
   - Use mocks in tests; never call real providers during automated tests.

5. **Evaluation and optimization**
   - If the PDF defines quality metrics, test cases, scoring, feedback, or optimization loops, represent them as versioned API/database concepts.
   - Preserve reproducibility by recording the AgentSpec version, compiler, input, configuration, evaluator version, scores, and produced artifacts for every run.

6. **Registration and governance**
   - Clarify what “registration” means in the document and implement the required lifecycle, metadata, ownership, validation, and audit fields.
   - Do not invent authentication or billing behavior, but leave clean extension points if the PDF requires identity, ownership, or permissions later.

7. **Traceability**
   - Add a short traceability section to `README.md` mapping each major PDF requirement to an endpoint, schema, service, migration, or test.
   - If a PDF requirement cannot be implemented yet, create a clearly named TODO with its reason and proposed next step instead of silently omitting it.

After reading the PDF, begin your response with a concise “PDF understanding” summary, then provide the implementation plan, changed files, migrations, tests, and any assumptions.
