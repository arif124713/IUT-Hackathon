"""
Shared test fixtures.

Must set DATABASE_URL before any `backend.app.*` module is imported anywhere in the
test session, since `backend.app.db` builds its engine at import time and
`backend.app.config.get_settings()` is `lru_cache`d. conftest.py is always imported
by pytest before test modules, so this env override wins.
"""
import os
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TEST_DB = _ROOT / "backend" / "tests" / "_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ["DEMO_MODE"] = "true"

import pytest_asyncio  # noqa: E402

from backend.app.db import init_db  # noqa: E402
from backend.app.simulator import seed_devices  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _seeded_db():
    await init_db()
    await seed_devices()
    yield
    if _TEST_DB.exists():
        _TEST_DB.unlink()
