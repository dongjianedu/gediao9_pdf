import os
import re

import html as _html


def load_template(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


def fill_template(template_html, fields):
    def _repl(m):
        key = m.group(1)
        val = fields.get(key)
        if val is None:
            print(f"  [WARN] {{FILL:{key}}} 未填充")
            return m.group(0)
        return str(val)

    return re.sub(r"\{\{FILL:(\w+)\}\}", _repl, template_html)


def write_html(html, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def escape_text(text):
    return _html.escape(text or "").replace("\n", "<br>")