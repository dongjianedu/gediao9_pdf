import os

from .base import PageGenerator
from ..core.text_utils import norm, find_breakpoint, norm_to_orig, parse_section_full, fmt_raw_qa
from ..core.pdf_ops import merge_first_pages, extract_column, extract_all_text


class Page5Generator(PageGenerator):
    template_file = "template_page_5.html"
    html_name = "page_5.html"
    pdf_name = "page_5_final.pdf"

    def generate(self, data, prev_pdfs):
        if len(prev_pdfs) < 4:
            raise RuntimeError("需要 page_1/2/3/4 的 PDF")

        merged_path = os.path.join(self.output_dir, "_merged5_temp.pdf")
        merge_first_pages(prev_pdfs[:4], merged_path)

        p0r = extract_column(merged_path, 0, "right")
        p1a = extract_all_text(merged_path, 1)
        p2r = extract_column(merged_path, 2, "right")
        p3r = extract_column(merged_path, 3, "right")
        rp1 = "\n".join([p0r, p1a, p2r, p3r])

        fp1 = parse_section_full(data.full_text, "PART1")
        cp1 = find_breakpoint(norm(rp1), norm(fp1), tail_len=50, max_dist=5)
        if cp1 < 0:
            cp1 = len(norm(fp1))
        rc = fp1[norm_to_orig(fp1, cp1):]

        p2l = extract_column(merged_path, 2, "left")
        p3l = extract_column(merged_path, 3, "left")
        rp2 = "\n".join([p2l, p3l])
        fp2 = parse_section_full(data.full_text, "PART2")
        cp2 = find_breakpoint(norm(rp2), norm(fp2), tail_len=50, max_dist=5)
        if cp2 < 0:
            cp2 = len(norm(fp2))
        lc = fp2[norm_to_orig(fp2, cp2):]

        fields = {
            "left_text": fmt_raw_qa(lc),
            "right_q4_question": "",
            "right_q4_answer": fmt_raw_qa(rc),
            "guest_image": self._resolve_image_small(data.image_dir, "page5"),
        }

        html = self.fill(fields)
        self.write(html)
        return html