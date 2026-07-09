#!/usr/bin/env bash
#
# check_env.sh - 检查 Ubuntu 服务器是否满足 gediao9_pdf 部署依赖
# 用法: bash check_env.sh
# 只读检查，不修改任何文件。全部通过退出码 0，有 FAIL 退出码 1。
#
set -u

PASS=0
WARN=0
FAIL=0

# 颜色
if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[0;33m'; NC='\033[0m'
else
    GREEN=''; RED=''; YEL=''; NC=''
fi

ok()   { echo -e "${GREEN}[OK]${NC}   $1"; PASS=$((PASS+1)); }
warn() { echo -e "${YEL}[WARN]${NC} $1"; WARN=$((WARN+1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }

# 比较版本号 a >= b，返回 0 表示满足
version_ge() {
    local a="$1" b="$2"
    [ "$a" = "$b" ] && return 0
    local IFS=.
    local i
    local a_arr=($a) b_arr=($b)
    local max=$(( ${#a_arr[@]} > ${#b_arr[@]} ? ${#a_arr[@]} : ${#b_arr[@]} ))
    for (( i=0; i<max; i++ )); do
        local an=${a_arr[i]:-0}
        local bn=${b_arr[i]:-0}
        # 去掉可能的非数字后缀（如 1.60.0.post1）
        an=${an%%[!0-9]*}
        bn=${bn%%[!0-9]*}
        an=${an:-0}; bn=${bn:-0}
        if (( an > bn )); then return 0; fi
        if (( an < bn )); then return 1; fi
    done
    return 0
}

# 检查 Python 包: pkg_dist_name min_version
check_pkg() {
    local dist="$1" min="$2"
    local ver
    ver=$(python3 -c "import importlib.metadata as m; print(m.version('$dist'))" 2>/dev/null)
    if [ -z "$ver" ]; then
        fail "Python 包缺失: $dist (要求 >= $min)  →  pip install -e .  或  pip install -e \".[api]\""
        return
    fi
    if version_ge "$ver" "$min"; then
        ok "Python 包 $dist == $ver (>= $min)"
    else
        fail "Python 包版本过低: $dist == $ver (要求 >= $min)  →  pip install --upgrade $dist"
    fi
}

echo "============================================"
echo " gediao9_pdf 部署环境检查"
echo "============================================"

# 1. OS 版本 (仅提示)
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if echo "$PRETTY_NAME" | grep -qi "ubuntu 20.04"; then
        ok "操作系统: $PRETTY_NAME"
    else
        warn "操作系统: $PRETTY_NAME （脚本按 Ubuntu 20.04 编写，其他版本可能需调整）"
    fi
else
    warn "无法识别操作系统 (/etc/os-release 不存在)"
fi

# 2. Python 版本
PYBIN=""
if command -v python3 >/dev/null 2>&1; then
    PYBIN=python3
elif command -v python >/dev/null 2>&1; then
    PYBIN=python
fi
if [ -z "$PYBIN" ]; then
    fail "未找到 python3  →  sudo apt update && sudo apt install python3.9 python3.9-venv"
else
    PYVER=$($PYBIN -c "import sys; print('%d.%d.%d' % sys.version_info[:3])")
    if version_ge "$PYVER" "3.9.0"; then
        ok "Python 版本: $PYVER (>= 3.9.0)  [命令: $PYBIN]"
    else
        fail "Python 版本过低: $PYVER (要求 >= 3.9.0)  →  sudo apt install python3.9"
    fi
fi

# 3. pip
if [ -n "$PYBIN" ] && $PYBIN -m pip --version >/dev/null 2>&1; then
    ok "pip 可用: $($PYBIN -m pip --version 2>&1 | head -1)"
else
    fail "pip 不可用  →  sudo apt install python3-pip"
fi

# 4-11. Python 包
check_pkg "PyMuPDF"          "1.23.0"
check_pkg "pdfplumber"        "0.10.0"
check_pkg "playwright"        "1.40.0"
check_pkg "openai"            "1.0.0"
check_pkg "fastapi"           "0.100.0"
check_pkg "uvicorn"           "0.20.0"
check_pkg "python-multipart"  "0.0.5"
check_pkg "Jinja2"            "3.0.0"

# 12. Playwright Chromium 浏览器
if [ -z "$PYBIN" ]; then
    warn "跳过 Chromium 检查（python 不可用）"
else
    if $PYBIN -m playwright install --dry-run chromium >/dev/null 2>&1; then
        ok "Playwright Chromium 浏览器已安装"
    else
        fail "Playwright Chromium 未安装  →  $PYBIN -m playwright install chromium"
    fi
    # 系统依赖（Ubuntu 需要，缺失会导致 chromium 启动崩溃）
    if [ -f /etc/os-release ]; then
        if ! ldconfig -p 2>/dev/null | grep -q libnss3.so; then
            warn "系统库 libnss3 可能缺失  →  sudo apt install libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2  (或 sudo $PYBIN -m playwright install-deps)"
        fi
    fi
fi

# 13. 项目已安装 (可导入 gediao9_pdf)
if [ -n "$PYBIN" ]; then
    if $PYBIN -c "import gediao9_pdf" >/dev/null 2>&1; then
        ok "项目 gediao9_pdf 可导入（已 pip install -e .）"
    else
        fail "项目未安装/不可导入  →  cd 项目目录 && pip install -e .  (含 api 用: pip install -e \".[api]\")"
    fi
fi

# 14. .env 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PATH="$(cd "$SCRIPT_DIR/.." && pwd)/.env"
if [ -f "$ENV_PATH" ]; then
    missing=""
    for k in OSS_ACCESS_KEY_ID OSS_ACCESS_KEY_SECRET OSS_ENDPOINT OSS_BUCKET_NAME OPENAI_API_KEY OPENAI_BASE_URL MODEL; do
        if ! grep -q "^${k}=" "$ENV_PATH"; then
            missing="$missing $k"
        fi
    done
    if [ -z "$missing" ]; then
        ok ".env 配置完整 (含 OSS / LLM 必需项)"
    else
        warn ".env 缺少必需项:$missing  →  cp .env.example .env 并补全"
    fi
else
    warn ".env 不存在  →  cp .env.example .env 并填入密钥"
fi

echo "============================================"
echo " 汇总: 通过 $PASS | 警告 $WARN | 失败 $FAIL"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
else
    exit 0
fi