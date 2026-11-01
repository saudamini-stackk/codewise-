import os
import tempfile
import pytest

# Point tests to an isolated temporary test database so production DB is never polluted
test_db = tempfile.NamedTemporaryFile(suffix="_codewise_test.db", delete=False)
test_db.close()
os.environ["CODEWISE_DB_PATH"] = test_db.name

from backend.app.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    init_db()
    yield
    try:
        if os.path.exists(test_db.name):
            os.remove(test_db.name)
    except Exception:
        pass
