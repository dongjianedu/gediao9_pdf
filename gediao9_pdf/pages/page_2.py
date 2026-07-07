import os
import re
import html as _html

from .base import PageGenerator
from ..core.text_utils import norm, find_breakpoint, norm_to_orig
from ..core.pdf_ops import extract_column, extract_all_text


class Page2Generator(PageGenerator):
    template_file = "template_page_2.html"
    html_name = "page_2.html"
    pdf_name = "page_2_final.pdf"

    def generate(self, data, prev_pdfs):
        if not prev_pdfs or not os.path.exists(prev_pdfs[0]):
            raise FileNotFoundError("page_1_final.pdf 不存在，请先生成第1页")

        rendered = extract_column(prev_pdfs[0], 0, "right")
        if not rendered:
            raise RuntimeError("第1页右栏提取失败")

        rendered_norm = norm(rendered)
        full_norm = norm(data.full_text)

        cutoff_norm = find_breakpoint(rendered_norm, full_norm, tail_len=50, max_dist=5)
        if cutoff_norm == -1:
            cutoff_norm = 0
        cutoff_orig = norm_to_orig(data.full_text, cutoff_norm)
        remaining = data.full_text[cutoff_orig:]

        remaining_questions = list(re.finditer(r"\n(\d+)[\.\u3001\uff0e]\s*(.+)", remaining))

        if len(remaining_questions) >= 1 and int(remaining_questions[0].group(1)) == 2:
            q1_remaining = remaining[:remaining_questions[0].start()].strip()
        else:
            q1_remaining = remaining.strip()

        q2_question_text = ""
        q2_answer_text = ""
        q3_section = ""

        for i, rm in enumerate(remaining_questions):
            q_num = int(rm.group(1))
            q_text = rm.group(2).strip()
            ans_start = rm.end()
            ans_end = remaining_questions[i + 1].start() if i + 1 < len(remaining_questions) else len(remaining)
            ans_text = remaining[ans_start:ans_end].strip()

            if q_num == 2:
                q2_question_text = f"2. {q_text}"
                q2_answer_text = ans_text
            elif q_num == 3:
                q3_section = f'\n\n<div class="question">3. {q_text}</div>\n{ans_text}'
                break

        fields = {
            "career_story": _html.escape(q1_remaining).replace("\n", "<br>"),
            "q2_question":  _html.escape(q2_question_text),
            "q2_answer":    _html.escape(q2_answer_text + q3_section).replace("\n", "<br>"),
        }

        html = self.fill(fields)
        self.write(html)
        return html