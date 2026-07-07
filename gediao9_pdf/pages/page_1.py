import os
import html as _html
import time

from .base import PageGenerator
from ..data.parsers import extract_intro, extract_q1_question, count_chars


MAX_RETRY = 3
BIO_COMPRESS_STEP = 40


class Page1Generator(PageGenerator):
    template_file = "template_page_1.html"
    html_name = "page_1.html"
    pdf_name = "page_1_final.pdf"

    def __init__(self, templates_dir, output_dir, llm_client=None, llm_model=None):
        super().__init__(templates_dir, output_dir)
        self.llm_client = llm_client
        self.llm_model = llm_model

    def generate(self, data, prev_pdfs):
        intro = extract_intro(data.full_text)
        q1_question = extract_q1_question(data.full_text)
        guest_image = self._resolve_image(data.image_dir, "page1")

        fields = {
            "header_date": _html.escape(data.date or ""),
            "subtitle_html": (
                f"格调人物九问系列访谈 | "
                f"特约采访人 {data.interviewer} | "
                f"本期采访嘉宾 {data.guest}"
            ),
            "bio": _html.escape(data.bio).replace("\n", "<br>"),
            "part_title": "PART1.格调九问<br>「人生轨迹与核心价值」",
            "q1_question": _html.escape(q1_question or ""),
            "intro_text": _html.escape(intro or "").replace("\n", "<br>"),
            "guest_image": guest_image,
        }

        html = self.fill(fields)
        self.write(html)
        return html

    def compress_bio(self, original_bio, target_chars):
        original_len = count_chars(original_bio)
        lower = max(1, target_chars - 10)
        print(f"  [LLM] 压缩简介: {original_len}字 -> {target_chars}字 (范围 {lower}~{target_chars})")

        messages = [
            {"role": "user", "content": (
                f"将以下个人简介精简到 {lower}~{target_chars} 字之间。\n"
                f"字数要求：\n"
                f"- 最终字数必须在 {lower}~{target_chars} 字范围内，超出区间不合格\n"
                f"- 优先接近 {target_chars} 字，但绝不能超过\n"
                f"- 保持姓名、出生年份、学历、工作履历、核心成就不变\n"
                f"- 去掉修饰性词语，语言简洁流畅\n"
                f"- 只输出精简后的简介文本，不要任何说明、标题或前缀\n\n"
                f"原始简介（{original_len}字）：\n{original_bio}"
            )}
        ]

        results = []
        for attempt in range(1, 4):
            try:
                t0 = time.time()
                response = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                result = response.choices[0].message.content.strip() if response.choices else ""
                result_len = count_chars(result)
                elapsed = time.time() - t0
                print(f"     {elapsed:.1f}s  {result_len}字 (差{abs(result_len - target_chars)}字)")
            except Exception as e:
                print(f"  [FAIL] LLM: {e}")
                if attempt == 1:
                    return None
                break

            results.append((result, result_len))
            if lower <= result_len <= target_chars:
                print(f"  [OK] 达标!")
                return result

            if attempt < 3:
                if result_len < lower:
                    messages.append({"role": "assistant", "content": result})
                    messages.append({"role": "user", "content": f"当前字数{result_len}字，不足，需增加约{lower - result_len}字。请在保持核心信息不丢失的前提下，适当补充细节或描述，使字数达到约{target_chars}字。只输出完整简介。"})
                else:
                    messages.append({"role": "assistant", "content": result})
                    messages.append({"role": "user", "content": f"当前字数{result_len}字，超出{result_len - target_chars}字。请进一步精简，删除非核心的修饰性词语，使字数降到约{target_chars}字。只输出完整简介。"})

        best = min(results, key=lambda x: abs(x[1] - target_chars))
        print(f"  [PICK] 最接近: {best[1]}字")
        return best[0]