import re


def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    m, n = len(s1), len(s2)
    prev = list(range(n + 1))
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev
    return prev[n]


def fuzzy_find(query, text, max_dist=None, hint=None, hint_radius=500):
    if not query or not text:
        return -1, float("inf")
    qlen, tlen = len(query), len(text)
    if qlen > tlen:
        return -1, float("inf")

    if hint is not None:
        lo = max(0, hint - hint_radius)
        hi = min(tlen - qlen, hint + hint_radius)
    else:
        lo = 0
        hi = tlen - qlen

    best_start = -1
    best_dist = float("inf")
    for start in range(lo, hi + 1):
        window = text[start:start + qlen]
        dist = levenshtein_distance(query, window)
        if dist < best_dist:
            best_dist = dist
            best_start = start
            if dist == 0:
                break

    if max_dist is not None and best_dist > max_dist:
        return -1, best_dist
    return best_start, best_dist


def find_breakpoint(rendered_text, full_text, tail_len=50, max_dist=5):
    if not rendered_text:
        return 0
    if not full_text:
        return 0

    tail = rendered_text[-tail_len:] if len(rendered_text) > tail_len else rendered_text
    hint = len(rendered_text) - tail_len
    start, dist = fuzzy_find(tail, full_text, max_dist, hint=hint)
    if start == -1:
        return -1
    return start + len(tail)


def norm(text):
    return re.sub(r"\s+", "", text)


def norm_to_orig(text, cutoff_norm):
    if cutoff_norm < 0:
        cutoff_norm = 0
    count = 0
    for i, ch in enumerate(text):
        if count >= cutoff_norm:
            return i
        if ch not in " \n\r\t":
            count += 1
    return len(text)


def clean_qa_text(text):
    text = re.sub(r"=== 第 \d+ 页 ===\s*", "", text)
    text = re.sub(r"【本题字数[：:].+?】\s*", "", text)
    return text.strip()


def detect_split_x(words):
    if isinstance(words[0], dict):
        x0s = [w["x0"] for w in words]
    else:
        x0s = [w[0] for w in words]
    if len(x0s) < 4:
        return None
    sorted_x0s = sorted(x0s)
    mid = len(sorted_x0s) // 2
    c1 = sum(sorted_x0s[:mid]) / mid
    c2 = sum(sorted_x0s[mid:]) / (len(sorted_x0s) - mid)
    for _ in range(5):
        g1 = [x for x in sorted_x0s if abs(x - c1) < abs(x - c2)]
        g2 = [x for x in sorted_x0s if abs(x - c1) >= abs(x - c2)]
        if not g1 or not g2:
            break
        c1 = sum(g1) / len(g1)
        c2 = sum(g2) / len(g2)
    return (c1 + c2) / 2


def rebuild_text(words):
    lines = {}
    for w in words:
        row = round(w["top"] / 10) * 10
        lines.setdefault(row, []).append(w)
    text = ""
    for row in sorted(lines):
        text += "".join(w["text"] for w in sorted(lines[row], key=lambda w: w["x0"]))
    return text


def parse_section_full(full_text, section_name):
    start = full_text.find(section_name)
    if start == -1:
        return ""
    content = full_text[start:]
    next_marker = re.search(r"\n(PART\d|$)", content[len(section_name):])
    if next_marker:
        content = content[:len(section_name) + next_marker.start()]
    return content


def parse_raw_qa(full_text, section_name, limit=None):
    section = parse_section_full(full_text, section_name)
    if not section:
        return []
    questions = list(re.finditer(r"\n(\d+)[\.\u3001\uff0e]\s*(.+)", section))
    qas = []
    for i, m in enumerate(questions):
        q_num = int(m.group(1))
        q_text = f"{q_num}. {m.group(2).strip()}"
        ans_start = m.end()
        ans_end = questions[i + 1].start() if i + 1 < len(questions) else len(section)
        ans_text = section[ans_start:ans_end].strip()
        qas.append({"num": q_num, "question": q_text, "answer": ans_text})
        if limit and len(qas) >= limit:
            break
    return qas


def parse_header_date(full_text):
    for line in full_text.split("\n"):
        if line.startswith("时间："):
            return line.split("：", 1)[1].strip()
    return ""


def fmt_raw_qa(text):
    text = re.sub(r"(^|\n)(\d+)[\.\u3001\uff0e]\s*(.+)", r'\1<div class="question">\2. \3</div>', text)
    text = text.replace("\n", "<br>")
    text = re.sub(r"<br>(?=<div class=\"question\">)", "", text)
    text = re.sub(r"(?<=</div>)<br>", "", text)
    text = re.sub(r"(<br>){2,}", "<br>", text)
    return text


def fmt_text_to_html(text):
    return text.replace("\n", "<br>")