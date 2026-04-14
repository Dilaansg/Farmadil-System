# Farmadil System Project Guidelines

## Build and Test
- Primary local run command: `python run.py`.
- Alternate run command: `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`.
- Run tests after backend changes: `pytest`.
- Lint and format before finishing non-trivial changes:
  - `ruff check . --fix`
  - `ruff format .`
- For schema/model changes, use Alembic workflow:
  - `alembic revision --autogenerate -m "<message>"`
  - `alembic upgrade head`
- If environment variables are missing, start from `.env.example`.

## Architecture
- App entrypoint is `main.py`; `run.py` is the preferred launcher for local development.
- Keep layer boundaries:
  - Routes in `app/api/v1/routes/` handle HTTP and dependency wiring.
  - Services in `app/services/` own business rules and validation.
  - Repositories in `app/repositories/` own database queries and persistence.
  - Models in `app/models/` define SQLModel tables.
  - Schemas in `app/schemas/` define request/response contracts.
- Reuse dependency aliases from `app/dependencies/` (for example `SessionDep`) instead of recreating injection patterns.

## Conventions
- Keep async flow end-to-end in API, services, and repositories (`AsyncSession`, async functions).
- Preserve soft-delete behavior:
  - Models inherit `AuditableBase` (`created_at`, `updated_at`, `is_deleted`).
  - Repository reads must filter out deleted rows (`is_deleted == False`).
- Perform domain validation in services and raise `HTTPException` with specific status codes and clear details.
- Keep runtime configuration in `app/core/config.py` and use `settings` instead of ad hoc environment reads.
- Follow existing route behavior when endpoints support both JSON and form payloads (HTMX-compatible flows).

## Project Pitfalls
- For UTC values, use `datetime.timezone.utc` (avoid `datetime.UTC` compatibility issues in this project context).
- Startup runs table creation and a lightweight product-column migration in `app/core/database.py`; do not add duplicate ad hoc startup migrations.
- Development commonly uses SQLite; keep Alembic and runtime URL handling aligned with `database_url_sync` and `database_url_async`.

## Key References
- System status and scope: [DESCRIPCION_SISTEMA.md](../DESCRIPCION_SISTEMA.md)
- Migration process: [MIGRACIONES_ALEMBIC.md](../MIGRACIONES_ALEMBIC.md)
- Implementation roadmap: [plan de ejecucion v.04.md](../plan%20de%20ejecucion%20v.04.md)
- Invoice ingestion strategy: [SCRAPING_STRATEGY.md](../SCRAPING_STRATEGY.md)
- Practical architecture tour: [F0_readme.md](../F0_readme.md)

## Pattern Files
- API router composition: `app/api/v1/__init__.py`
- Dependency/session pattern: `app/dependencies/db.py`
- Repository soft-delete query style: `app/repositories/user_repository.py`
- Service validation and HTTP errors: `app/services/product_service.py`
- Test dependency overrides and async client: `app/tests/conftest.py`
