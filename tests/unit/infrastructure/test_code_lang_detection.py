"""Tests for the language detection in the Markdown renderer."""

from __future__ import annotations

from pdf2md.infrastructure.renderers.markdown_renderer import _detect_code_lang


class TestDetectCodeLang:
    def test_detects_vue_sfc_with_template(self) -> None:
        cells = [
            "<template>",
            "<div>{{ msg }}</div>",
            "</template>",
            "<script setup>",
            "const msg = 'hi'",
            "</script>",
        ]
        assert _detect_code_lang(cells) == "vue"

    def test_detects_html(self) -> None:
        cells = [
            "<html>",
            "<body>",
            "<div>Hello</div>",
            "</body>",
            "</html>",
        ]
        assert _detect_code_lang(cells) == "html"

    def test_detects_python(self) -> None:
        cells = [
            "def hello():",
            "    print('hi')",
            "    return 0",
        ]
        assert _detect_code_lang(cells) == "python"

    def test_detects_bash(self) -> None:
        cells = [
            "$ npm install",
            "$ yarn dev",
            "$ cd Chapter01/",
        ]
        assert _detect_code_lang(cells) == "bash"

    def test_detects_sql(self) -> None:
        cells = [
            "SELECT id, name FROM users WHERE active = 1;",
            "INSERT INTO logs (msg) VALUES ('x');",
        ]
        assert _detect_code_lang(cells) == "sql"

    def test_detects_json(self) -> None:
        cells = [
            "{",
            '  "name": "test",',
            '  "items": [1, 2, 3]',
            "}",
        ]
        assert _detect_code_lang(cells) == "json"

    def test_detects_css(self) -> None:
        cells = [
            ".form {",
            "  display: flex;",
            "  padding: 20px;",
            "}",
        ]
        assert _detect_code_lang(cells) == "css"

    def test_detects_typescript_with_vue_directives(self) -> None:
        """A <script> with v-bind and v-model: prefer vue over ts."""
        cells = [
            "<script setup>",
            "const title = ref('hi')",
            "</script>",
            "<template>",
            "<div v-bind:src=\"logo\" v-model=\"name\" />",
            "</template>",
        ]
        assert _detect_code_lang(cells) == "vue"

    def test_falls_back_to_ts_for_plain_typescript(self) -> None:
        cells = [
            "const x: number = 1;",
            "interface Foo { bar: string; }",
            "function baz(): void { return; }",
        ]
        assert _detect_code_lang(cells) == "ts"

    def test_falls_back_to_empty_for_empty_cells(self) -> None:
        assert _detect_code_lang([]) == ""
        assert _detect_code_lang(["", "  "]) == ""
