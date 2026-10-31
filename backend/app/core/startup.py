"""Database startup: create tables, detect a stale schema loudly, optionally rebuild, then seed.

``create_all`` adds missing tables but never missing columns, so a SQLite file created by an
older version of the models keeps working until a query touches a new column, and the
auto-seed then fails with an obscure error. This module detects that case up front, says so
plainly (log, ``/health``), refuses to seed into a broken schema, and can optionally rebuild
the file (keeping the old one as a timestamped backup).
"""

import logging
import os
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

# The uvicorn.error logger is always shown on the server console.
logger = logging.getLogger("uvicorn.error")

STALE_BANNER = (
    "DATABASE SCHEMA IS OUT OF DATE. The API will run, but seeding was skipped and some "
    "pages will fail until this is fixed."
)


@dataclass
class StartupReport:
    schema_issues: List[str] = field(default_factory=list)
    rebuilt_backup: Optional[str] = None
    seeded: bool = False
    seed_error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.schema_issues and not self.seed_error


def detect_schema_drift(engine: Engine) -> List[str]:
    """Columns the current models expect but the existing tables do not have."""
    import app.models.entities  # noqa: F401  (registers every model on the metadata)

    inspector = inspect(engine)
    issues: List[str] = []
    for table in SQLModel.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # create_all creates missing tables
        have = {c["name"] for c in inspector.get_columns(table.name)}
        missing = [c.name for c in table.columns if c.name not in have]
        if missing:
            issues.append(f"table '{table.name}' is missing column(s): {', '.join(missing)}")
    return issues


def rebuild_sqlite(engine: Engine) -> Optional[str]:
    """Move a SQLite file aside and create a fresh schema. Returns the backup path."""
    if engine.dialect.name != "sqlite":
        return None
    path = engine.url.database
    if not path or path == ":memory:" or not os.path.exists(path):
        return None
    engine.dispose()
    backup = f"{path}.stale-{datetime.now():%Y%m%d-%H%M%S}.bak"
    shutil.move(path, backup)
    SQLModel.metadata.create_all(engine)
    return backup


def _log_stale(issues: List[str], rebuild_failed: Optional[str]) -> None:
    lines = [STALE_BANNER] + [f"  - {i}" for i in issues]
    if rebuild_failed:
        lines.append(f"  Automatic rebuild failed: {rebuild_failed}")
        lines.append("  Stop every server using this database file and try again.")
    lines.append(
        "  Fix: stop the server, move backend/optisched.db aside (it is gitignored), restart. "
        "Or start with REBUILD_STALE_DB=true to do that automatically; the old file is kept "
        "as optisched.db.stale-<timestamp>.bak."
    )
    logger.error("\n".join(lines))


def prepare_database(
    engine: Engine,
    *,
    auto_seed: bool,
    rebuild_stale: bool,
    seed: Optional[Callable[[], object]] = None,
) -> StartupReport:
    import app.models.entities  # noqa: F401

    SQLModel.metadata.create_all(engine)
    report = StartupReport()
    issues = detect_schema_drift(engine)
    rebuild_error: Optional[str] = None

    if issues and rebuild_stale:
        try:
            report.rebuilt_backup = rebuild_sqlite(engine)
        except OSError as exc:
            rebuild_error = f"{type(exc).__name__}: {exc}"
        if report.rebuilt_backup:
            logger.warning(
                "Rebuilt the stale database. The previous file was kept as %s", report.rebuilt_backup
            )
            issues = detect_schema_drift(engine)

    report.schema_issues = issues
    if issues:
        _log_stale(issues, rebuild_error)
        return report  # never seed into a broken schema

    if auto_seed:
        if seed is None:
            from app.core.seeder import seed_database

            seed = seed_database
        try:
            seed()
            report.seeded = True
        except Exception as exc:
            report.seed_error = f"{type(exc).__name__}: {exc}"
            logger.error(
                "Auto-seed FAILED (%s). The database is up but may be empty or partial.",
                report.seed_error,
            )
    return report


def start_warmup(engine: Engine) -> threading.Thread:
    """Solve the baseline and prime Claude in the background so the first demo click is fast."""

    def run() -> None:
        from sqlmodel import Session

        from app.services.copilot_service import llm_enabled, load_vocabulary, parse_prompt
        from app.services.scenario_service import ScenarioSpec, simulate_scenario

        try:
            with Session(engine) as session:
                simulate_scenario(session, ScenarioSpec())
                logger.info("Warm-up: baseline timetable solved and cached.")
                if llm_enabled():
                    parse_prompt("warm up: CS enrollment grows 1%", load_vocabulary(session))
                    logger.info("Warm-up: Claude structured-output schema primed.")
        except Exception as exc:  # warm-up must never take the server down
            logger.warning("Warm-up skipped: %s: %s", type(exc).__name__, exc)

    thread = threading.Thread(target=run, name="demo-warmup", daemon=True)
    thread.start()
    return thread
