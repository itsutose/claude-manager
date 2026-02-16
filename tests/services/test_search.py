"""search.py のテスト."""
from __future__ import annotations

from claude_manager.services.search import _calc_score, search_sessions
from tests.factories import make_clone, make_group, make_session


class TestCalcScore:
    def test_display_name_match(self):
        s = make_session(custom_title="fizzbuzz実装")
        score = _calc_score(s, "fizzbuzz", "my-project", "my-project")
        assert score >= 10

    def test_display_name_prefix_bonus(self):
        s = make_session(custom_title="fizzbuzz実装")
        score_prefix = _calc_score(s, "fizzbuzz", "g", "c")
        s2 = make_session(custom_title="XXXfizzbuzz")
        score_mid = _calc_score(s2, "fizzbuzz", "g", "c")
        assert score_prefix > score_mid

    def test_first_prompt_match(self):
        s = make_session(custom_title=None, first_prompt="Pythonでfizzbuzzを書いて")
        score = _calc_score(s, "fizzbuzz", "g", "c")
        assert score > 0

    def test_git_branch_match(self):
        s = make_session(git_branch="feature/auth")
        score = _calc_score(s, "auth", "g", "c")
        assert score >= 2

    def test_no_match(self):
        s = make_session(custom_title="テスト", first_prompt="テスト")
        score = _calc_score(s, "zzz", "g", "c")
        assert score == 0

    def test_group_name_match(self):
        s = make_session()
        score = _calc_score(s, "myproj", "myproject", "clone")
        assert score >= 1


class TestSearchSessions:
    def _make_groups(self):
        s1 = make_session(session_id="s1", custom_title="fizzbuzz実装")
        s2 = make_session(session_id="s2", custom_title="テスト追加", first_prompt="pytestのテスト")
        s3 = make_session(session_id="s3", custom_title="README作成")
        clone = make_clone(sessions=[s1, s2, s3])
        return [make_group(clones=[clone])]

    def test_basic_search(self):
        groups = self._make_groups()
        results = search_sessions(groups, "fizzbuzz")
        assert len(results) >= 1
        assert results[0]["session_id"] == "s1"

    def test_empty_query(self):
        groups = self._make_groups()
        assert search_sessions(groups, "") == []

    def test_no_results(self):
        groups = self._make_groups()
        results = search_sessions(groups, "zzzznotfound")
        assert results == []

    def test_max_results(self):
        groups = self._make_groups()
        results = search_sessions(groups, "テスト", max_results=1)
        assert len(results) <= 1

    def test_result_has_expected_keys(self):
        groups = self._make_groups()
        results = search_sessions(groups, "fizzbuzz")
        assert len(results) > 0
        r = results[0]
        assert "session_id" in r
        assert "group_name" in r
        assert "score" in r
