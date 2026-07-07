import os
import sys
import random

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPT_DIR)

from gediao9_pdf.core.text_utils import (
    levenshtein_distance,
    fuzzy_find,
    find_breakpoint,
    norm,
    norm_to_orig,
    clean_qa_text,
)

pass_count = 0
fail_count = 0


def check(desc, actual, expected):
    global pass_count, fail_count
    if actual == expected:
        pass_count += 1
        print(f"  PASS  {desc}")
    else:
        fail_count += 1
        print(f"  FAIL  {desc}")
        print(f"        expected={repr(expected)}")
        print(f"        actual  ={repr(actual)}")


def check_approx(desc, actual, expected, tolerance):
    global pass_count, fail_count
    if abs(actual - expected) <= tolerance:
        pass_count += 1
        print(f"  PASS  {desc}")
    else:
        fail_count += 1
        print(f"  FAIL  {desc}")
        print(f"        expected={expected} \u00b1{tolerance}")
        print(f"        actual  ={actual}")


def test_levenshtein():
    print("\n[test_levenshtein]")
    check("identical ascii", levenshtein_distance("abc", "abc"), 0)
    check("identical chinese", levenshtein_distance("\u4f60\u597d\u4e16\u754c", "\u4f60\u597d\u4e16\u754c"), 0)
    check("one substitution", levenshtein_distance("abc", "axc"), 1)
    check("one deletion", levenshtein_distance("abc", "ab"), 1)
    check("one insertion", levenshtein_distance("ab", "abc"), 1)
    check("all different", levenshtein_distance("abc", "xyz"), 3)
    check("empty s1", levenshtein_distance("", "abc"), 3)
    check("empty s2", levenshtein_distance("abc", ""), 3)
    check("chinese 2 substitutions", levenshtein_distance("\u4f60\u597d\u4e16\u754c", "\u4f60\u597d\u5730\u7403"), 2)
    check("mixed cn_en", levenshtein_distance("IT\u884c\u4e1a", "IT \u884c\u4e1a"), 1)


def test_fuzzy_find():
    print("\n[test_fuzzy_find]")
    full_text = "".join(chr(0x4e00 + i) for i in range(2500))
    full_norm = norm(full_text)

    snippet_start = 300
    snippet = full_norm[snippet_start:snippet_start + 50]

    check("exact match - distance 0",
          fuzzy_find(snippet, full_norm),
          (snippet_start, 0))

    mutated1 = list(snippet)
    mutated1[10] = "X"
    mutated1 = "".join(mutated1)
    start1, dist1 = fuzzy_find(mutated1, full_norm, max_dist=3)
    check("1-char mutation - found", start1 >= 0 and dist1 <= 3, True)

    mutated3 = snippet[:-3]
    start3, dist3 = fuzzy_find(mutated3, full_norm, max_dist=5)
    check("3-char deletion - found", start3 >= 0 and dist3 <= 5, True)

    bad_query = "X" * 50
    start_bad, _ = fuzzy_find(bad_query, full_norm, max_dist=3)
    check("no match - exceeds max_dist", start_bad, -1)

    head_snippet = full_norm[:50]
    check("head match", fuzzy_find(head_snippet, full_norm), (0, 0))

    tail_snippet = full_norm[-50:]
    check("tail match", fuzzy_find(tail_snippet, full_norm),
          (len(full_norm) - 50, 0))


def test_find_breakpoint():
    print("\n[test_find_breakpoint]")
    full_text = "".join(chr(0x4e00 + i) for i in range(2500))
    full_norm = norm(full_text)

    rendered = full_norm[:2000]
    cutoff = find_breakpoint(rendered, full_norm, tail_len=50, max_dist=3)
    check("exact breakpoint at 2000", cutoff, 2000)

    random.seed(42)
    rendered_list = list(rendered)
    mutation_indices = random.sample(range(len(rendered_list)), min(5, len(rendered_list)))
    for idx in mutation_indices:
        rendered_list[idx] = "\u5f00"
    mutated_rendered = "".join(rendered_list)
    cutoff_mut = find_breakpoint(mutated_rendered, full_norm, tail_len=50, max_dist=10)
    check_approx("breakpoint with 5 mutations", cutoff_mut, 2000, 20)

    check("empty rendered returns 0",
          find_breakpoint("", full_norm, tail_len=50, max_dist=3), 0)

    try:
        cutoff_long = find_breakpoint(full_norm, full_norm[:20], tail_len=50, max_dist=3)
        check("query longer than full_text", cutoff_long, -1)
    except Exception as e:
        fail_count += 1
        print(f"  FAIL  query longer than full_text -- crash: {e}")


def test_norm():
    print("\n[test_norm]")
    check("strip spaces", norm("a b c"), "abc")
    check("strip newlines", norm("a\nb\nc"), "abc")
    check("strip mixed whitespace", norm(" a \t b \r\n c "), "abc")
    check("all whitespace returns empty", norm("  \n\t  "), "")


def test_norm_to_orig():
    print("\n[test_norm_to_orig]")
    text = "a b c"
    check("norm[0]->orig[0]", norm_to_orig(text, 0), 0)
    check("norm[1]->orig[1]", norm_to_orig(text, 1), 1)
    check("norm[2]->orig[3]", norm_to_orig(text, 2), 3)
    check("beyond text returns len(text)", norm_to_orig(text, 100), len(text))


def test_clean_qa():
    print("\n[test_clean_qa]")
    text1 = "=== 第 1 页 ===\n\u91c7\u8bbf\u5bf9\u8c61\uff1a\u9ec4\u65b0\u5f3a\n\n=== 第 2 页 ===\n\u6b63\u6587\u5185\u5bb9"
    result1 = clean_qa_text(text1)
    check("removes page markers", "=== 第" not in result1, True)
    check("preserves content after clean",
          "\u91c7\u8bbf\u5bf9\u8c61\uff1a\u9ec4\u65b0\u5f3a" in result1 and "\u6b63\u6587\u5185\u5bb9" in result1, True)

    text2 = "\u56de\u7b54\u95ee\u9898...\n\u3010\u672c\u9898\u5b57\u6570\uff1a2100 \u5b57\uff0c\u76ee\u6807\uff1a2000~3000 \u5b57\u3011\n\u4e0b\u4e00\u6bb5"
    result2 = clean_qa_text(text2)
    check("removes word count marker", "\u672c\u9898\u5b57\u6570" not in result2, True)


if __name__ == "__main__":
    test_levenshtein()
    test_fuzzy_find()
    test_find_breakpoint()
    test_norm()
    test_norm_to_orig()
    test_clean_qa()

    total = pass_count + fail_count
    print(f"\n{'=' * 50}")
    print(f"  TOTAL: {pass_count}/{total} passed"
          + (f", {fail_count} FAILED" if fail_count else " -- ALL PASS"))
    print(f"{'=' * 50}")