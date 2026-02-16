"""sessions ルーターのテスト."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestGetSession:
    @pytest.mark.anyio
    async def test_found(self, client: AsyncClient):
        resp = await client.get("/api/sessions/sess-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-001"
        assert "group_name" in data
        assert "clone_name" in data

    @pytest.mark.anyio
    async def test_not_found(self, client: AsyncClient):
        resp = await client.get("/api/sessions/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestTogglePin:
    @pytest.mark.anyio
    async def test_pin_toggle(self, client: AsyncClient):
        resp = await client.put("/api/sessions/sess-001/pin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_pinned"] is True

        # トグルで解除
        resp2 = await client.put("/api/sessions/sess-001/pin")
        data2 = resp2.json()
        assert data2["is_pinned"] is False


class TestRenameSession:
    @pytest.mark.anyio
    async def test_rename(self, client: AsyncClient):
        resp = await client.put(
            "/api/sessions/sess-001/title",
            json={"title": "新しい名前"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "新しい名前"

    @pytest.mark.anyio
    async def test_rename_not_found(self, client: AsyncClient):
        resp = await client.put(
            "/api/sessions/nonexistent/title",
            json={"title": "x"},
        )
        data = resp.json()
        assert "error" in data


class TestHideSession:
    @pytest.mark.anyio
    async def test_hide(self, client: AsyncClient):
        resp = await client.post("/api/sessions/sess-001/hide")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hidden"] is True

    @pytest.mark.anyio
    async def test_unhide(self, client: AsyncClient):
        await client.post("/api/sessions/sess-001/hide")
        resp = await client.post("/api/sessions/sess-001/unhide")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hidden"] is False
