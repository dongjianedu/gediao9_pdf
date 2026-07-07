import os
import html as _html

from .base import PageGenerator
from ..core.text_utils import norm, find_breakpoint, norm_to_orig, parse_section_full, fmt_raw_qa
from ..core.pdf_ops import merge_first_pages, extract_column, extract_all_text


class Page6Generator(PageGenerator):
    template_file = "template_page_6_new.html"
    html_name = "page_6.html"
    pdf_name = "page_6_final.pdf"

    def generate(self, data, prev_pdfs):
        if len(prev_pdfs) < 5:
            raise RuntimeError("需要 page_1/2/3/4/5 的 PDF")

        merged_path = os.path.join(self.output_dir, "_merged6_temp.pdf")
        merge_first_pages(prev_pdfs[:5], merged_path)

        p0r = extract_column(merged_path, 0, "right")
        p1a = extract_all_text(merged_path, 1)
        p2r = extract_column(merged_path, 2, "right")
        p3r = extract_column(merged_path, 3, "right")
        p4r = extract_column(merged_path, 4, "right")
        rp1 = "\n".join([p0r, p1a, p2r, p3r, p4r])

        fp1 = parse_section_full(data.full_text, "PART1")
        cp1 = find_breakpoint(norm(rp1), norm(fp1), tail_len=50, max_dist=5)
        if cp1 < 0:
            cp1 = len(norm(fp1))
        rc = fp1[norm_to_orig(fp1, cp1):]

        p2l = extract_column(merged_path, 2, "left")
        p3l = extract_column(merged_path, 3, "left")
        p4l = extract_column(merged_path, 4, "left")
        rp2 = "\n".join([p2l, p3l, p4l])
        fp2 = parse_section_full(data.full_text, "PART2")
        cp2 = find_breakpoint(norm(rp2), norm(fp2), tail_len=50, max_dist=5)
        if cp2 < 0:
            cp2 = len(norm(fp2))
        lc = fp2[norm_to_orig(fp2, cp2):]

        footer_html = self._build_footer(data.guest, data.interviewer)

        fields = {
            "left_q3_question": "",
            "left_q3_answer": fmt_raw_qa(lc),
            "right_q5_question": "",
            "right_q5_answer": fmt_raw_qa(rc),
            "page_footer": footer_html,
        }

        html = self.fill(fields)
        self.write(html)
        return html

    @staticmethod
    def _build_footer(guest, interviewer):
        g = _html.escape(guest)
        i = _html.escape(interviewer)
        return (
            f"<p>以上是本期格调人物采访嘉宾{g}的访谈，"
            f"如果你对{g}有兴趣或者有合作需求，"
            f"或者希望接受人物专访、参与人物专访。</p>"
            f"<p>欢迎联络：采访人 {i}（微信：zhihuiguoxiangqing）</p>"
        )