import os
import sys
import time

import fitz

from ..config import get_llm_client, TEMPLATES_DIR, OUTPUT_DIR
from ..data.parsers import parse_input_dir, count_chars
from ..core.pdf_ops import render_pdf, get_page_count, has_bio_overflow
from ..pages.page_1 import Page1Generator, MAX_RETRY, BIO_COMPRESS_STEP
from ..pages.page_2 import Page2Generator
from ..pages.page_3 import Page3Generator
from ..pages.page_4 import Page4Generator
from ..pages.page_5 import Page5Generator
from ..pages.page_6 import Page6Generator


def run_pipeline(input_dir, output_dir=None, page=None, no_llm=False):
    if output_dir is None:
        output_dir = os.path.join(input_dir, "..", "output")
    output_dir = os.path.abspath(output_dir)
    input_dir = os.path.abspath(input_dir)

    print(f"[INFO] 输入: {input_dir}")
    print(f"[INFO] 输出: {output_dir}")

    data = parse_input_dir(input_dir)
    print(f"  嘉宾: {data.guest}  采访人: {data.interviewer}  ({data.date})")
    print(f"  简介: {count_chars(data.bio)} 字")
    print(f"  PART1: {len(data.part1_qa)} 问  PART2: {len(data.part2_qa)} 问")

    llm_client, llm_model = None, None
    if not no_llm:
        try:
            llm_client, llm_model = get_llm_client()
            print(f"  LLM: {llm_model}")
        except Exception:
            print("  [WARN] 无法加载 LLM 配置，将跳过压缩")

    pages_1_6 = [
        Page1Generator(TEMPLATES_DIR, output_dir, llm_client, llm_model),
        Page2Generator(TEMPLATES_DIR, output_dir),
        Page3Generator(TEMPLATES_DIR, output_dir),
        Page4Generator(TEMPLATES_DIR, output_dir),
        Page5Generator(TEMPLATES_DIR, output_dir),
        Page6Generator(TEMPLATES_DIR, output_dir),
    ]

    if page is not None:
        pages_1_6 = [pages_1_6[page - 1]]

    prev_pdfs = []
    for idx, gen in enumerate(pages_1_6):
        page_num = page if page else idx + 1
        print(f"\n{'=' * 50}")
        print(f"[Page {page_num}] {gen.__class__.__name__}")

        if page_num == 1:
            _run_page1(gen, data, prev_pdfs)
        else:
            gen.generate(data, prev_pdfs)
            gen.render()

        prev_pdfs.append(gen.pdf_path)
        print(f"  [OK] {gen.pdf_path}")

    merged_pdf = os.path.join(output_dir, "all_pages.pdf")
    merge = fitz.open()
    for pdf_path in prev_pdfs:
        if os.path.exists(pdf_path):
            doc = fitz.open(pdf_path)
            merge.insert_pdf(doc, from_page=0, to_page=0)
            doc.close()
            print(f"  + {os.path.basename(pdf_path)}")
    merge.save(merged_pdf)
    merge.close()

    print(f"\n{'=' * 50}")
    print(f"[DONE] 全部完成! 输出目录: {output_dir}")
    print(f"  合并 PDF: {merged_pdf}")


def _run_page1(gen, data, prev_pdfs):
    original_bio = data.bio
    bio = original_bio
    MAX_ATTEMPTS = MAX_RETRY

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  [RETRY] 第 {attempt}/{MAX_ATTEMPTS} 轮 (简介 {count_chars(bio)} 字)")

        data.bio = bio
        gen.generate(data, prev_pdfs)

        round_pdf = os.path.join(gen.output_dir, f"page_1_r{attempt}.pdf")
        try:
            gen.render(round_pdf)
        except Exception as e:
            print(f"  [FAIL] PDF 渲染失败: {e}")
            break

        over, _ = has_bio_overflow(round_pdf)
        pages = get_page_count(round_pdf)
        print(f"  [PAGES] {pages} 页, 溢出={over}")

        if not over:
            gen.render(gen.pdf_path)
            print(f"  [OK] bio 收敛在第1页! ({count_chars(bio)} 字)")
            return

        bio_len = count_chars(bio)
        target = max(1, bio_len - BIO_COMPRESS_STEP)
        print(f"  [WARN] 内容溢出! ({bio_len}字 -> 目标 {target}字)")

        if attempt == MAX_ATTEMPTS:
            print(f"  [WARN] 已达最大重试次数，保留当前 {bio_len} 字版本")
        else:
            new_bio = _compress_bio(gen, original_bio, target)
            if new_bio is not None:
                bio = new_bio
            else:
                print("  [WARN] 压缩失败，保留当前版本")

    data.bio = bio
    gen.generate(data, prev_pdfs)
    gen.render(gen.pdf_path)
    print(f"  [WARN] 循环结束，输出当前版本 ({count_chars(bio)} 字)")


def _compress_bio(gen, original_bio, target):
    if gen.llm_client is not None:
        return gen.compress_bio(original_bio, target)
    return None