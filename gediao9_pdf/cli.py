import argparse
import sys

from .core.engine import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="格调九问 PDF 排版生成工具")
    parser.add_argument("input_dir", nargs="?", help="输入目录 (含 *的格调9问.txt 和 *的自我介绍.txt)")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("--page", type=int, choices=range(1, 7), help="只生成指定页 (1-6)")
    parser.add_argument("--no-llm", action="store_true", help="禁用 LLM 压缩")

    args = parser.parse_args()

    if not args.input_dir:
        parser.print_help()
        sys.exit(1)

    run_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output,
        page=args.page,
        no_llm=args.no_llm,
    )


if __name__ == "__main__":
    main()