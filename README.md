# gediao9_pdf

格调九问 PDF 排版生成工具。将采访数据（自我介绍 + 格调九问）自动排版为 6 页 A4 PDF。

## 环境要求

- Python 3.9+
- conda base 环境
- Playwright Chromium（`playwright install chromium`）

## 安装

```bash
cd gediao9_pdf
pip install -e .
playwright install chromium
```

## 配置 LLM

复制 `.env.example` 为 `.env` 并填入 API 密钥：

```bash
cp .env.example .env
```

`.env` 内容：

```
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.deepseek.com
MODEL=deepseek-v4-pro
```

## 使用

```bash
# 生成全部 6 页 + 合并 PDF
python -m gediao9_pdf.cli <input_dir>

# 只生成指定页
python -m gediao9_pdf.cli <input_dir> --page 1

# 指定输出目录
python -m gediao9_pdf.cli <input_dir> -o <output_dir>

# 禁用 LLM 压缩
python -m gediao9_pdf.cli <input_dir> --no-llm
```

## 输入格式

输入目录需包含以下文件：

```
<input_dir>/
  X的格调9问.txt    # 采访对象名 + 格调9问，含 PART1/PART2 标记
  X的自我介绍.txt    # 第三人称个人简介
  page1.jpg          # 可选，封面图片
  page3.jpg          # 可选，第 3 页图片
  page5.jpg          # 可选，第 5 页图片
```

## 输出

```
<output_dir>/
  page_1.html / page_1_final.pdf   # 封面（含 LLM 自适应简介压缩）
  page_2.html / page_2_final.pdf   # 职业经历
  page_3.html / page_3_final.pdf   # 延展篇
  page_4.html / page_4_final.pdf   # 延续
  page_5.html / page_5_final.pdf   # 延续
  page_6.html / page_6_final.pdf   # 收尾 + 联系信息
  all_pages.pdf                    # 合并后的 6 页 PDF
```

## 工作流程

```
TXT 数据 → 解析 → 自适应断点填充 → HTML 模板 → Playwright → PDF
              ↑
         LLM 压缩（page1: 简介溢出时自动压缩）
```

## 测试

```bash
# 单元测试
python tests/test_utils.py
```

## 项目结构

```
gediao9_pdf/
├── cli.py                  # 命令行入口
├── config.py               # 环境变量 + 路径配置
├── core/
│   ├── engine.py           # 6 页顺序流水线
│   ├── template.py         # 模板引擎 ({{FILL:key}})
│   ├── pdf_ops.py          # PDF 合并/提取/渲染/溢出检测
│   └── text_utils.py       # 编辑距离/模糊匹配/双栏检测
├── data/
│   ├── models.py           # InterviewData 数据模型
│   └── parsers.py          # TXT 数据解析
├── pages/
│   ├── base.py             # PageGenerator 抽象基类
│   ├── page_1.py           # 封面（含 LLM 压缩）
│   ├── page_2.py           # 职业经历
│   ├── page_3.py           # 延展篇
│   ├── page_4.py           # 延续
│   ├── page_5.py           # 延续
│   └── page_6.py           # 收尾 + footer
└── templates/              # 6 个 HTML 模板
```