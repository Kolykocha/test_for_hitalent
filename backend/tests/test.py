from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import api.endpoints.department as departments_endpoint 
from db import get_db

pytestmark = pytest.mark.asyncio


class _FakeQuery:
    def __init__(
        self,
        *,
        first_result=None,
        all_result=None,
        count_result=None,
        update_result=None,
        delete_result=None,
    ) -> None:
        self._first_result = first_result
        self._all_result = all_result
        self._count_result = count_result
        self._update_result = update_result
        self._delete_result = delete_result

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result

    def all(self):
        return self._all_result if self._all_result is not None else []

    def count(self):
        return self._count_result if self._count_result is not None else 0

    def update(self, *args, **kwargs):
        return self._update_result if self._update_result is not None else 1

    def delete(self, *args, **kwargs):
        return self._delete_result if self._delete_result is not None else 1


class _FakeDB:
    def __init__(self) -> None:
        self._queries = []
        self._add_calls = []
        self._commit_calls = 0
        self._refresh_calls = []
        self._rollback_calls = 0

    def add(self, obj):
        self._add_calls.append(obj)
        return obj

    def commit(self):
        self._commit_calls += 1

    def refresh(self, obj):
        self._refresh_calls.append(obj)
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 999  
        return obj

    def rollback(self):
        self._rollback_calls += 1

    def query(self, *args, **kwargs):
        assert self._queries, f"Unexpected extra db.query() call. Remaining: {len(self._queries)}"
        return self._queries.pop(0)


def _build_app(fake_db: _FakeDB) -> FastAPI:
    app = FastAPI()
    app.include_router(departments_endpoint.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: fake_db
    return app


#Тесты для POST /departments

class TestCreateDepartment:
    async def test_create_department_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест успешного создания подразделения"""
        fake_db = _FakeDB()
        
        # Мокаем запрос на проверку существования дубликата
        fake_db._queries.append(_FakeQuery(first_result=None))  # нет дубликата
        
        app = _build_app(fake_db)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/departments/", json={
                "name": "New Department",
                "parent_id": None
            })
        
        assert response.status_code == 201
        payload = response.json()
        assert payload["name"] == "New Department"
        assert payload["parent_id"] is None
        assert "id" in payload
        assert "created_at" in payload

        assert len(fake_db._add_calls) == 1
        assert fake_db._commit_calls == 1
        assert len(fake_db._refresh_calls) == 1

    async def test_create_department_with_parent_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест создания подразделения с родителем"""
        fake_db = _FakeDB()
        
        parent_dept = SimpleNamespace(id=5, name="Parent Dept")
        
        fake_db._queries.append(_FakeQuery(first_result=None))  
        
        app = _build_app(fake_db)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/departments/", json={
                "name": "Child Department",
                "parent_id": 5
            })
        
        assert response.status_code == 201
        payload = response.json()
        assert payload["name"] == "Child Department"
        assert payload["parent_id"] == 5

    async def test_create_department_duplicate_name_same_parent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Тест создания дубликата с тем же родителем"""
        fake_db = _FakeDB()
        
        existing_dept = SimpleNamespace(id=10, name="Duplicate Dept", parent_id=1)
        
        fake_db._queries.append(_FakeQuery(first_result=existing_dept))
        
        app = _build_app(fake_db)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/departments/", json={
                "name": "Duplicate Dept",
                "parent_id": 1
            })
        
        assert response.status_code == 400
        payload = response.json()
        assert "Department name is exists" in payload["detail"]
        
        assert len(fake_db._add_calls) == 0
        assert fake_db._commit_calls == 0
