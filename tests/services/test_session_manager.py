"""session_manager._generate_title のテスト."""
from claude_manager.services.session_manager import SessionManager


class TestGenerateTitle:
    """SessionManager._generate_title の純粋関数テスト."""

    def setup_method(self):
        # _generate_title は self.config を使わないのでダミーで OK
        self.mgr = SessionManager(config=None)  # type: ignore[arg-type]

    def test_simple_text(self):
        assert self.mgr._generate_title("fizzbuzzを書いて") == "fizzbuzzを書いて"

    def test_empty_returns_nameless(self):
        assert self.mgr._generate_title("") == "(名前なし)"

    def test_none_input(self):
        assert self.mgr._generate_title(None) == "(名前なし)"  # type: ignore[arg-type]

    def test_long_text_truncated(self):
        title = self.mgr._generate_title("あ" * 30)
        assert len(title) <= 20

    def test_xml_tag_block_removed(self):
        title = self.mgr._generate_title("<context>長い文脈</context>本題はこれ")
        assert "<" not in title
        assert "本題" in title

    def test_xml_only_returns_nameless(self):
        title = self.mgr._generate_title("<tag>content</tag>")
        assert title == "(名前なし)"

    def test_markdown_link_kept_text(self):
        title = self.mgr._generate_title("[リンクテキスト](https://example.com)を修正")
        assert "リンクテキスト" in title
        assert "https" not in title

    def test_url_removed(self):
        title = self.mgr._generate_title("https://example.com/foo/bar を開いて")
        assert "https" not in title
        assert "開いて" in title

    def test_file_path_removed(self):
        title = self.mgr._generate_title("/Users/test/my-project/src/main.py を修正")
        assert "/Users" not in title
        assert "修正" in title

    def test_sentence_cut_at_period(self):
        title = self.mgr._generate_title("修正して。あとテスト")
        assert title == "修正して"

    def test_newline_normalized_to_space(self):
        title = self.mgr._generate_title("修正して\nあとテスト")
        # 改行はスペースに正規化される（セパレータ分割より前）
        assert title == "修正して あとテスト"

    def test_file_url_removed(self):
        title = self.mgr._generate_title("file:///Users/test/foo.txt を確認")
        assert "file:///" not in title

    def test_at_sign_removed(self):
        title = self.mgr._generate_title("@user に聞いて")
        assert "@" not in title

    def test_short_text_after_cleanup_returns_nameless(self):
        title = self.mgr._generate_title("< >")
        assert title == "(名前なし)"
