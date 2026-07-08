# 使用 Python 官方镜像
FROM python:3.11-slim

# 安装 Playwright 所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Chromium（Playwright 生成 PDF 所需）
RUN playwright install chromium && playwright install-deps chromium

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "gediao9_pdf.api:app", "--host", "0.0.0.0", "--port", "8000"]
