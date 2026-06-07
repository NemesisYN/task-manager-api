import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
import asyncio
import asyncpg
from main import app, DATABASE_URL

# Глобальная очистка базы (запускается один раз перед всеми тестами)
@pytest.fixture(scope="session", autouse=True)
def clean_db_once():
    clean_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    loop = asyncio.get_event_loop()
    async def clean():
        conn = await asyncpg.connect(clean_url)
        await conn.execute("TRUNCATE users, tasks RESTART IDENTITY CASCADE;")
        await conn.close()
    loop.run_until_complete(clean())
    yield

client = TestClient(app)

# --- Тесты ---
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_register_user():
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "123456"
    })
    assert response.status_code == 200
    assert "id" in response.json()

def test_about():
    responce = client.get("/about")
    assert responce.status_code == 200
    assert responce.json() == {"version": 1.0, "author": "NemesisYN"}