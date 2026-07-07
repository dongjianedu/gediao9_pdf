import os
import glob
import re

from .models import InterviewData
from ..core.text_utils import clean_qa_text, parse_raw_qa


def count_chars(text):
    return len(text.replace(" ", "").replace("\n", "").strip())


def parse_input_dir(dir_path):
    qa_files = glob.glob(os.path.join(dir_path, "*的格调9问.txt"))
    bio_files = glob.glob(os.path.join(dir_path, "*的自我介绍.txt"))

    if not qa_files:
        raise FileNotFoundError(f"未找到 *的格调9问.txt: {dir_path}")
    if not bio_files:
        raise FileNotFoundError(f"未找到 *的自我介绍.txt: {dir_path}")

    qa_path = qa_files[0]
    bio_path = bio_files[0]

    with open(bio_path, "r", encoding="utf-8") as f:
        bio = f.read().strip()

    with open(qa_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    clean = clean_qa_text(full_text)

    metadata = {}
    for line in clean.split("\n"):
        if not line.strip():
            continue
        if line.startswith("PART1"):
            break
        if line.startswith("格调九问"):
            continue
        if "：" in line:
            k, v = line.split("：", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                metadata[k] = v

    part1 = _extract_section(full_text, "PART1")
    part2 = _extract_section(full_text, "PART2")

    data = InterviewData(
        guest=metadata.get("采访对象", ""),
        interviewer=metadata.get("采访人", ""),
        date=metadata.get("时间", ""),
        bio=bio,
        full_text=full_text,
        image_dir=dir_path,
        part1=part1,
        part2=part2,
        part1_qa=parse_raw_qa(full_text, "PART1"),
        part2_qa=parse_raw_qa(full_text, "PART2"),
    )
    return data


def extract_intro(full_text):
    clean = clean_qa_text(full_text)
    pos = clean.find("PART1")
    if pos < 0:
        return ""

    rest = clean[pos:]
    m = re.search(
        r"1[\.\u3001\uff0e]\s*请简单介绍.+?[;?\uff1b\uff1f]?\s*\n(.+?)(?=\n\d+[\.\u3001\uff0e]\s|\nPART2|\Z)",
        rest, re.DOTALL,
    )
    if not m:
        return ""

    text = m.group(1).strip()
    return _smart_truncate(text)


def extract_q1_question(full_text):
    qas = parse_raw_qa(full_text, "PART1", limit=1)
    if not qas:
        return ""
    return qas[0]["question"]


def _extract_section(full_text, section_name):
    start = full_text.find(section_name)
    if start == -1:
        return ""
    content = full_text[start:]
    next_marker = re.search(r"\n(PART\d|$)", content[len(section_name):])
    if next_marker:
        content = content[:len(section_name) + next_marker.start()]
    return content


def _smart_truncate(text, max_chars=500):
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_boundary = max(
        truncated.rfind("\u3002"),
        truncated.rfind("\uff1f"),
        truncated.rfind("\uff01"),
        truncated.rfind("\uff1b"),
        truncated.rfind(";"),
        truncated.rfind("\n"),
    )
    if last_boundary > max_chars * 0.5:
        return text[:last_boundary + 1].strip()
    return truncated.strip()