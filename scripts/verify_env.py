#!/usr/bin/env python3
"""gediao9_pdf 环境最小验证脚本 — Ubuntu 服务器专用
用法: python3 verify_env.py
零外部文件依赖，所有测试数据内嵌，临时目录用完自动清理。
"""

import sys
import os
import tempfile
import shutil

PASS = 0
FAIL = 0


def ok(msg):
    global PASS; PASS += 1; print(f"\033[32m[OK]\033[0m   {msg}")


def fl(msg):
    global FAIL; FAIL += 1; print(f"\033[31m[FAIL]\033[0m {msg}")


def skip(msg):
    print(f"\033[33m[SKIP]\033[0m {msg}")


print("=" * 60)
print(" gediao9_pdf 环境验证")
print("=" * 60)

# ====== 1. Python 版本 ======
v = sys.version_info
print(f"  Python {v.major}.{v.minor}.{v.micro}  (仅信息)")

# ====== 2. 关键包导入 ======
_pkgs = [
    ("fitz",       "PyMuPDF"),
    ("pdfplumber", "pdfplumber"),
    ("playwright", "playwright"),
    ("openai",     "openai"),
    ("oss2",       "oss2"),
    ("fastapi",    "fastapi"),
    ("uvicorn",    "uvicorn"),
]

for mod, name in _pkgs:
    try:
        __import__(mod)
        ok(f"import {name}")
    except ImportError:
        fl(f"import {name} 失败  →  pip install {name}")

# ====== 3. Jinja2 (fastapi 模板引擎依赖) ======
try:
    __import__("jinja2")
    ok("import jinja2")
except ImportError:
    fl("import jinja2 失败  →  pip install jinja2")

# ====== 4. python-multipart ======
try:
    __import__("multipart")
    ok("import python-multipart")
except ImportError:
    fl("import python-multipart 失败  →  pip install python-multipart")

# ====== 5. Playwright Chromium 浏览器 ======
try:
    from playwright.sync_api import sync_playwright

    p = sync_playwright().start()
    browser = p.chromium.launch()
    browser.close()
    p.stop()
    ok("Playwright Chromium 可启动")
except Exception as e:
    fl(f"Playwright Chromium 启动失败: {e}")
    fl("  → playwright install chromium")
    fl("  → 如仍失败: sudo python3 -m playwright install-deps")

# ====== 6. 核心引擎 PDF 生成（使用内嵌测试数据） ======
try:
    from gediao9_pdf.core.engine import run_pipeline

    indir = tempfile.mkdtemp(prefix="verify_")
    outdir = tempfile.mkdtemp(prefix="verify_out_")

    guest = "\u5f20\u4e09"  # 张三
    bio = f"{guest}\uff0c\u521b\u59cb\u4eba\uff0c\u6bd5\u4e1a\u4e8e\u6e05\u534e\u5927\u5b66\uff0c\u66fe\u4efb\u67d0\u4e92\u8054\u7f51\u516c\u53f8\u6280\u672f\u603b\u76d1\u3002\n"
    bio += "2023\u5e74\u521b\u7acbAI\u516c\u53f8\uff0c\u81f4\u529b\u4e8e\u5927\u6a21\u578b\u5e94\u7528\u843d\u5730\u3002"

    qa = "\u683c\u8c03\u4e5d\u95ee\u4eba\u7269\u4e13\u8bbf\n"
    qa += f"\u91c7\u8bbf\u5bf9\u8c61\uff1a{guest}\n"
    qa += "\u91c7\u8bbf\u4eba\uff1a\u6d4b\u8bd5\u5458\n"
    qa += "\u65f6\u95f4\uff1a2026\u5e741\u6708\n"
    qa += "PART1.\u683c\u8c03\u4e5d\u95ee\n"
    qa += "1. \u8bf7\u7b80\u5355\u4ecb\u7ecd\u4e00\u4e0b\u60a8\u81ea\u5df1\n"
    qa += "\u5f20\u4e09\u7684\u56de\u7b54\u5185\u5bb9\uff0c\u5305\u542b\u4e2a\u4eba\u7ecf\u5386\u3001\u5de5\u4f5c\u5c65\u5386\u7b49\u4fe1\u606f\u3002"
    qa += "\u4ed6\u66fe\u5728\u77e5\u540d\u4e92\u8054\u7f51\u516c\u53f8\u62c5\u4efb\u6280\u672f\u603b\u76d1\uff0c\u8d1f\u8d23\u591a\u4e2a\u6838\u5fc3\u4ea7\u54c1\u7684\u7814\u53d1\u5de5\u4f5c\u3002\n"
    qa += "2. \u5206\u4eab\u4e00\u4e2a\u60a8\u505a\u5f97\u6700\u6210\u529f\u7684\u9879\u76ee\n"
    qa += "AI\u9879\u76ee\u5b9e\u73b0\u7528\u6237\u589e\u957f300%\uff0c\u5e26\u9886\u56e2\u961f\u4ece\u96f6\u5230\u4e00"

    bio_path = os.path.join(indir, f"{guest}\u7684\u81ea\u6211\u4ecb\u7ecd.txt")
    qa_path = os.path.join(indir, f"{guest}\u7684\u683c\u8c039\u95ee.txt")
    with open(bio_path, "w", encoding="utf-8") as f:
        f.write(bio)
    with open(qa_path, "w", encoding="utf-8") as f:
        f.write(qa)

    run_pipeline(input_dir=indir, output_dir=outdir, no_llm=True)

    merged = os.path.join(outdir, "all_pages.pdf")
    size = os.path.getsize(merged)
    ok(f"PDF \u751f\u6210\u6210\u529f ({size/1024:.0f} KB)")

    shutil.rmtree(indir, ignore_errors=True)
    shutil.rmtree(outdir, ignore_errors=True)
except ImportError:
    fl("gediao9_pdf \u672a\u5b89\u88c5  \u2192  cd \u9879\u76ee\u76ee\u5f55 && pip install -e .")
except Exception as e:
    fl(f"PDF \u751f\u6210\u5931\u8d25: {e}")

# ====== 7. OSS 模块（需 .env） ======
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(env_path):
    try:
        from gediao9_pdf.api import _upload_to_oss
        ok("OSS \u4e0a\u4f20\u51fd\u6570\u53ef\u5bfc\u5165")
    except Exception as e:
        skip(f"OSS \u6a21\u5757\u8df3\u8fc7 (api.py \u5bfc\u5165\u5931\u8d25: {e})")
else:
    skip(f"OSS \u8df3\u8fc7 ({env_path} \u4e0d\u5b58\u5728\uff0c\u90e8\u7f72\u540e\u518d\u9a8c\u8bc1)")

# ====== 汇总 ======
print("=" * 60)
print(f" \u901a\u8fc7 {PASS} / \u5931\u8d25 {FAIL}")
print("=" * 60)

if FAIL > 0:
    print("\n\u5931\u8d25\u9879\u8bf7\u6309\u63d0\u793a\u4fee\u590d\u540e\u91cd\u65b0\u8fd0\u884c\u672c\u811a\u672c\u3002")
    sys.exit(1)
else:
    print("\n\u73af\u5883\u9a8c\u8bc1\u901a\u8fc7\uff0c\u53ef\u4ee5\u90e8\u7f72\u8fd0\u884c\u3002")
    sys.exit(0)
