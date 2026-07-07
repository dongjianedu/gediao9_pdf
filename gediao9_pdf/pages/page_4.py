import os

from .base import PageGenerator
from ..core.text_utils import norm, find_breakpoint, norm_to_orig, parse_section_full, fmt_raw_qa
from ..core.pdf_ops import merge_first_pages, extract_column, extract_all_text


class Page4Generator(PageGenerator):
    template_file = "template_page_4.html"
    html_name = "page_4.html"
    pdf_name = "page_4_final.pdf"

    def generate(self, data, prev_pdfs):
        if len(prev_pdfs) < 3:
            raise RuntimeError("需要 page_1/2/3 的 PDF")

        merged_path = os.path.join(self.output_dir, "_merged4_temp.pdf")
        merge_first_pages(prev_pdfs[:3], merged_path)

        p0r = extract_column(merged_path, 0, "right")
        p1a = extract_all_text(merged_path, 1)
        p2r = extract_column(merged_path, 2, "right")
        rp1 = p0r + "\n" + p1a + "\n" + p2r

        fp1 = parse_section_full(data.full_text, "PART1")
        cp1 = find_breakpoint(norm(rp1), norm(fp1), tail_len=50, max_dist=5)
        if cp1 < 0:
            cp1 = len(norm(fp1))
        rc = fp1[norm_to_orig(fp1, cp1):]

        p2l = extract_column(merged_path, 2, "left")
        fp2 = parse_section_full(data.full_text, "PART2")
        cp2 = find_breakpoint(norm(p2l), norm(fp2), tail_len=50, max_dist=5)
        if cp2 < 0:
            cp2 = len(norm(fp2))
        lc = fp2[norm_to_orig(fp2, cp2):]

        fields = {
            "left_q2_question": "",
            "left_q2_answer": fmt_raw_qa(lc),
            "right_q3_question": "",
            "right_q3_answer": fmt_raw_qa(rc),
        }

        html = self.fill(fields)
        self.write(html)
        return html