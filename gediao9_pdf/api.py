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

from .core.engine import run_pipeline
from .config import load_env

app = FastAPI(title="格调九问 PDF 排版工具")

API_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(API_DIR, "templates"))

INPUT_BASE_DIR = r"D:\dev_tools\code\gediaoTemplate\gediao_temp_content"
DEFAULT_IMAGE_DIR = os.path.join(API_DIR, "static")

_oss_env = load_env()
OSS_CONFIG = {
    "access_key_id": _oss_env.get("OSS_ACCESS_KEY_ID", ""),
    "access_key_secret": _oss_env.get("OSS_ACCESS_KEY_SECRET", ""),
    "endpoint": _oss_env.get("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com"),
    "bucket_name": _oss_env.get("OSS_BUCKET_NAME", "gediao9"),
    "access_point_url": _oss_env.get("OSS_ACCESSPOINT_URL", ""),
}


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
    auth = oss2.Auth(OSS_CONFIG["access_key_id"], OSS_CONFIG["access_key_secret"])
    bucket = oss2.Bucket(auth, OSS_CONFIG["endpoint"], OSS_CONFIG["bucket_name"])
    bucket.put_object_from_file(object_key, local_file)
    return f"https://{OSS_CONFIG['bucket_name']}.{OSS_CONFIG['endpoint']}/{object_key}"


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

    import traceback

    try:
        await asyncio.to_thread(
            run_pipeline,
            input_dir=input_dir,
            output_dir=output_dir,
            no_llm=no_llm,
        )
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status_code=500)

    merged_pdf = os.path.join(output_dir, "all_pages.pdf")
    if not os.path.exists(merged_pdf):
        return JSONResponse({"error": "PDF 生成失败，请检查日志"}, status_code=500)

    safe_name = _sanitize_name(guest_name or "未命名")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    object_key = f"pdf/{safe_name}_{timestamp}/all_pages.pdf"

    try:
        oss_url = await asyncio.to_thread(_upload_to_oss, merged_pdf, object_key)
    except Exception as e:
        return JSONResponse({
            "error": f"PDF 上传到 OSS 失败: {str(e)}",
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