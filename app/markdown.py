"""Server-side Markdown → HTML renderer.

Uses markdown-it-py for parsing and Pygments for syntax highlighting.
Registered as a Jinja2 filter named 'markdown' in main.py.

Usage in templates: {{ msg.content | markdown | safe }}
"""

from markupsafe import Markup
from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

_formatter = HtmlFormatter(cssclass="highlight")


def _build_md() -> MarkdownIt:
    md = MarkdownIt("gfm-like", {"html": False, "typographer": True})
    md.enable(["table", "strikethrough"])
    md = md.use(tasklists_plugin)

    def _highlight(code: str, lang: str, _attrs: str) -> str:
        try:
            lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
        except ClassNotFound:
            lexer = guess_lexer(code)
        try:
            return highlight(code, lexer, _formatter)
        except Exception:
            return f"<pre><code>{code}</code></pre>"

    md.options["highlight"] = _highlight
    return md


_md = _build_md()


def render_markdown(text: str) -> Markup:
    """Convert Markdown text to safe HTML."""
    if not text:
        return Markup("")
    return Markup(_md.render(text))


def pygments_css() -> str:
    """Return the Pygments CSS string for the current formatter style."""
    return _formatter.get_style_defs(".highlight")
