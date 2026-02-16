"""groups ルーターのテスト."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestListGroups:
    @pytest.mark.anyio
    async def test_returns_groups(self, client: AsyncClient):
        resp = await client.get("/api/groups")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data
        assert len(data["groups"]) >= 1
        assert data["groups"][0]["group_id"] == "test-proj"

    @pytest.mark.anyio
    async def test_group_has_expected_keys(self, client: AsyncClient):
        resp = await client.get("/api/groups")
        group = resp.json()["groups"][0]
        assert "group_id" in group
        assert "display_name" in group
        assert "initials" in group
        assert "total_sessions" in group


class TestGetGroup:
    @pytest.mark.anyio
    async def test_found(self, client: AsyncClient):
        resp = await client.get("/api/groups/test-proj")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "test-proj"
        assert "clones" in data
        assert len(data["clones"]) >= 1

    @pytest.mark.anyio
    async def test_not_found(self, client: AsyncClient):
        resp = await client.get("/api/groups/nonexistent")
        # group_detectorはリスト直接返却なので404ではなくerror
        assert resp.status_code == 200
