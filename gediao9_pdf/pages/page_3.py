import os
import html as _html

from .base import PageGenerator
from ..core.text_utils import norm, find_breakpoint, norm_to_orig, parse_section_full, fmt_raw_qa
from ..core.pdf_ops import merge_first_pages, extract_column, extract_all_text


class Page3Generator(PageGenerator):
    template_file = "template_page_3.html"
    html_name = "page_3.html"
    pdf_name = "page_3_final.pdf"

    def generate(self, data, prev_pdfs):
        if len(prev_pdfs) < 2:
            raise RuntimeError("需要 page_1 + page_2 的 PDF")

        merged_path = os.path.join(self.output_dir, "_merged3_temp.pdf")
        merge_first_pages(prev_pdfs[:2], merged_path)

        p0r = extract_column(merged_path, 0, "right")
        p1a = extract_all_text(merged_path, 1)
        rendered_all = p0r + "\n" + p1a

        fp1 = parse_section_full(data.full_text, "PART1")
        cutoff = find_breakpoint(norm(rendered_all), norm(fp1), tail_len=50, max_dist=5)
        if cutoff < 0:
            cutoff = len(norm(fp1))
        right_continuation = fp1[norm_to_orig(fp1, cutoff):]
        right_html = fmt_raw_qa(right_continuation)

        p2_qas = data.part2_qa
        q1_text = ""
        q2_text = ""
        if len(p2_qas) >= 1:
            q1 = p2_qas[0]
            q1_text = _html.escape(q1["answer"]).replace("\n", "<br>")
        if len(p2_qas) >= 2:
            q2 = p2_qas[1]
            q2_text = _html.escape(q2["answer"]).replace("\n", "<br>")

        fields = {
            "part2_title": 'PART2. 延展篇<br>「个人特质与生活哲学」',
            "pa_q1_question": _html.escape(p2_qas[0]["question"]) if len(p2_qas) >= 1 else "",
            "pa_q1_answer": q1_text,
            "pa_q2_question": _html.escape(p2_qas[1]["question"]) if len(p2_qas) >= 2 else "",
            "pa_q2_answer": q2_text,
            "right_continuation": right_html,
            "guest_image": self._resolve_image_small(data.image_dir, "page3"),
        }

        html = self.fill(fields)
        self.write(html)
        return html