import asyncio
import os
import re
import tempfile
import shutil
import traceback
from datetime import datetime

import oss2
import uvicorn
from fastapi import FastAPI, Form, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .core.engine import run_pipeline
from .config import get_oss_config, INPUT_BASE_DIR

app = FastAPI(title="格调九问 PDF 排版工具")

API_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(API_DIR, "templates"))

DEFAULT_IMAGE_DIR = os.path.join(API_DIR, "static")

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]
ALLOWED_ORIGINS += ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run("gediao9_pdf.api:app", host="0.0.0.0", port=8000, reload=True)


def _cleanup(*dirs):
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)


def _sanitize_name(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name.strip())


def _copy_default_images(input_dir):
    for name in ("page3.jpg", "page5.jpg", "page7.jpg"):
        src = os.path.join(DEFAULT_IMAGE_DIR, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(input_dir, name))


def _upload_to_oss(local_file: str, object_key: str) -> str:
    import time

    oss_config = get_oss_config()
    if oss_config is None:
        raise RuntimeError("未配置 OSS 凭证（OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET）")
    print(
        f"[INFO] OSS 连接参数: bucket={oss_config['bucket_name']} "
        f"endpoint={oss_config['endpoint']}"
    )
    auth = oss2.Auth(oss_config["access_key_id"], oss_config["access_key_secret"])
    bucket = oss2.Bucket(auth, oss_config["endpoint"], oss_config["bucket_name"])
    # 部分旧版 oss2 不认构造函数的 timeout 参数；用模块级默认值做快速失败兜底
    try:
        oss2.defaults.connect_timeout = 10
        oss2.defaults.timeout = 60
    except Exception:
        pass
    start = time.time()
    bucket.put_object_from_file(object_key, local_file)
    elapsed = time.time() - start
    print(f"[INFO] put_object_from_file 完成，耗时 {elapsed:.1f}s")
    return f"https://{oss_config['bucket_name']}.{oss_config['endpoint']}/{object_key}"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    guest_name: str = Form(default=""),
    interviewer: str = Form(default=""),
    date: str = Form(default=""),
    bio: str = Form(default=""),
    qa_text: str = Form(default=""),
    no_llm: bool = Form(default=False),
    page1_image: UploadFile = File(default=None),
):
    input_dir = tempfile.mkdtemp(prefix="gediao9_")
    output_dir = tempfile.mkdtemp(prefix="gediao9_out_")
    background_tasks.add_task(_cleanup, input_dir, output_dir)

    bio_path = os.path.join(input_dir, f"{guest_name or '未命名'}的自我介绍.txt")
    with open(bio_path, "w", encoding="utf-8", newline='\n') as f:
        f.write(bio.strip())

    header = f"格调九问\n采访对象：{guest_name}\n采访人：{interviewer}\n时间：{date}\n\n"
    qa_content = header + qa_text.strip()
    qa_path = os.path.join(input_dir, f"{guest_name or '未命名'}的格调9问.txt")
    with open(qa_path, "w", encoding="utf-8", newline='\n') as f:
        f.write(qa_content)

    if page1_image is not None and page1_image.filename:
        content = await page1_image.read()
        with open(os.path.join(input_dir, "page1.jpg"), "wb") as f:
            f.write(content)

    _copy_default_images(input_dir)

    try:
        await asyncio.to_thread(
            run_pipeline,
            input_dir=input_dir,
            output_dir=output_dir,
            no_llm=no_llm,
        )
        print(f"[INFO] run_pipeline 完成，输出目录: {output_dir}")
    except Exception as e:
        print(f"[ERROR] run_pipeline 失败: {e}")
        print(traceback.format_exc())
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status_code=500)

    merged_pdf = os.path.join(output_dir, "all_pages.pdf")
    if not os.path.exists(merged_pdf):
        print(f"[ERROR] 未找到合并后的 PDF: {merged_pdf}")
        return JSONResponse({"error": "PDF 生成失败，请检查日志"}, status_code=500)

    safe_name = _sanitize_name(guest_name or "未命名")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_key = f"pdf/{safe_name}_{timestamp}/all_pages.pdf"

    print(f"[INFO] 开始上传 OSS: {object_key}")
    try:
        oss_url = await asyncio.wait_for(
            asyncio.to_thread(_upload_to_oss, merged_pdf, object_key),
            timeout=75,
        )
        print(f"[INFO] OSS 上传成功: {oss_url}")
    except asyncio.TimeoutError:
        print("[ERROR] OSS 上传超时（>75s），后端网络可能连不上 OSS")
        return JSONResponse({
            "error": "PDF 上传到 OSS 超时（>75s），请检查后端网络是否能访问 OSS",
            "traceback": traceback.format_exc(),
        }, status_code=500)
    except Exception as e:
        print(f"[ERROR] OSS 上传失败: {e}")
        print(traceback.format_exc())
        return JSONResponse({
            "error": f"PDF 上传到 OSS 失败: {str(e)}",
            "traceback": traceback.format_exc(),
        }, status_code=500)

    return JSONResponse({
        "success": True,
        "url": oss_url,
    })


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_files(
    guest_name: str = Form(default=""),
    bio: str = Form(default=""),
    qa_file: UploadFile = File(default=None),
    photo: UploadFile = File(default=None),
):
    if not guest_name.strip():
        return JSONResponse({"error": "嘉宾姓名不能为空"}, status_code=400)

    if qa_file is None or not qa_file.filename:
        return JSONResponse({"error": "请上传格调9问 TXT 文件"}, status_code=400)

    safe_name = _sanitize_name(guest_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{safe_name}_{timestamp}"
    output_dir = os.path.join(INPUT_BASE_DIR, dir_name)

    os.makedirs(output_dir, exist_ok=True)

    files_created = []

    if bio.strip():
        bio_path = os.path.join(output_dir, f"{guest_name}的自我介绍.txt")
        with open(bio_path, "w", encoding="utf-8") as f:
            f.write(bio.strip())
        files_created.append(os.path.basename(bio_path))

    qa_content = await qa_file.read()
    qa_path = os.path.join(output_dir, f"{guest_name}的格调9问.txt")
    with open(qa_path, "wb") as f:
        f.write(qa_content)
    files_created.append(os.path.basename(qa_path))

    if photo is not None and photo.filename:
        photo_content = await photo.read()
        photo_path = os.path.join(output_dir, "page1.jpg")
        with open(photo_path, "wb") as f:
            f.write(photo_content)
        files_created.append("page1.jpg")

    return JSONResponse({
        "success": True,
        "directory": output_dir,
        "files": files_created,
    })
