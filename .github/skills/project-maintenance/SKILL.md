---
name: project-maintenance
description: 'Use when changing the Farmadil System project, especially when adding new libraries, updating requirements.txt, or making major changes that require updating DESCRIPCION_SISTEMA.md.'
---

# Project Maintenance

## When to Use
- Add or update third-party Python libraries
- Make changes that require updating `requirements.txt`
- Make important code, architecture, database, or workflow changes
- Keep `DESCRIPCION_SISTEMA.md` aligned with the current system state

## Procedure
1. Check whether the change introduces any new external dependency.
2. If a new library is used, add it to `requirements.txt` and install it in the active virtual environment.
3. If the change is important enough to affect how the system is described, update `DESCRIPCION_SISTEMA.md` in the same change.
4. Verify the application still starts or the affected tests still pass.
5. Confirm that the documentation and dependency files match the implemented change.

## Completion Checks
- No new library is used without being recorded in `requirements.txt`
- `DESCRIPCION_SISTEMA.md` reflects major functional or architectural changes
- The venv and dependency list stay in sync with the codebase
