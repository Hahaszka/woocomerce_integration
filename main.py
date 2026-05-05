import os
import shutil
import uuid
import json
import io
import asyncio
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from typing import List, Optional
from woocommerce import API
from PIL import Image
import sheets_sync

app = FastAPI()

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

WOO_URL = os.getenv("WOO_URL", "http://wordpress")
WOO_KEY = os.getenv("WOO_KEY", "ck_placeholder_key")
WOO_SECRET = os.getenv("WOO_SECRET", "cs_placeholder_secret")
APP_HOST_URL = os.getenv("APP_HOST_URL", "http://localhost:9000")

IMAGE_META_KEY = "_image_urls"

print(f"Connecting to WooCommerce at: {WOO_URL}")
print(f"App host URL for uploaded images: {APP_HOST_URL}")

wcapi = API(
    url=WOO_URL,
    consumer_key=WOO_KEY,
    consumer_secret=WOO_SECRET,
    version="wc/v3",
    query_string_auth=True,
    verify_ssl=False
)
wcapi.is_ssl = True


def inject_meta_images(products: list) -> list:
    for product in products:
        meta = {m["key"]: m["value"] for m in product.get("meta_data", [])}
        image_urls_str = meta.get(IMAGE_META_KEY, "")
        if image_urls_str:
            product["images"] = [
                {"src": url.strip()}
                for url in image_urls_str.split(",")
                if url.strip()
            ]
    return products


@app.on_event("startup")
async def startup_event():
    print("Performing initial Google Sheets sync...")
    try:
        sheets_sync.full_sync(wcapi)
    except Exception as e:
        print(f"Initial sync failed: {e}")

    asyncio.create_task(periodic_sync_task())


async def periodic_sync_task():
    while True:
        await asyncio.sleep(600)  # 10 minutes
        print("Performing periodic Google Sheets sync...")
        try:
            sheets_sync.full_sync(wcapi)
        except Exception as e:
            print(f"Periodic sync failed: {e}")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"GOOGLE_SHEET_ID": sheets_sync.SHEET_ID}
    )


@app.get("/api/products")
async def get_products():
    response = wcapi.get("products", params={"per_page": 100})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch products")
    products = response.json()
    inject_meta_images(products)
    return products


async def get_images_from_form(form) -> list:
    """
    Collect all image URLs from the form.
    - images_json: raw external URLs (picsum, etc.) — used as-is
    - files: uploaded files — saved locally, URL = APP_HOST_URL/static/uploads/<filename>

    Returns a list of {"src": url} dicts. These are stored in WooCommerce meta_data,
    NOT in the WooCommerce images field, to avoid WP trying to download/re-host them.
    """
    images = []

    # 1. External URLs typed by the user
    images_json = form.get("images_json", "[]")
    if images_json:
        try:
            parsed_images = json.loads(images_json)
            if isinstance(parsed_images, list):
                images.extend(parsed_images)
        except Exception:
            pass

    files = form.getlist("files")
    for file in files:
        if isinstance(file, UploadFile) and file.filename:
            filename = f"{uuid.uuid4()}_{file.filename}"
            safe_filename = "".join(
                [c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]
            ).rstrip()

            base_name, _ = os.path.splitext(safe_filename)
            final_filename = f"{base_name}.jpg"
            filepath = os.path.join("static", "uploads", final_filename)

            try:
                content = await file.read()
                img = Image.open(io.BytesIO(content))

                # Compress & Resize (max 1920x1920, keeps aspect ratio)
                img.thumbnail((1920, 1920))

                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.save(filepath, "JPEG", quality=80)
            except Exception as e:
                print(f"Image compression failed: {e}")
                final_filename = safe_filename
                filepath = os.path.join("static", "uploads", final_filename)
                await file.seek(0)
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

            images.append({"src": f"{APP_HOST_URL}/static/uploads/{final_filename}"})

    return images


@app.post("/api/products")
async def create_product(request: Request):
    form = await request.form()
    name = form.get("name")
    regular_price = form.get("regular_price")
    description = form.get("description", "")

    if not name or not regular_price:
        raise HTTPException(status_code=400, detail="Name and regular_price are required")

    images = await get_images_from_form(form)
    images_value = ",".join(img["src"] for img in images)

    data = {
        "name": name,
        "type": "simple",
        "regular_price": regular_price,
        "description": description,
        "images": [],
        "meta_data": [
            {"key": IMAGE_META_KEY, "value": images_value}
        ]
    }
    response = wcapi.post("products", data)
    if response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to create product: {response.text}"
        )

    product = response.json()
    inject_meta_images([product])

    try:
        sheets_sync.sync_from_woo_to_sheets(wcapi)
    except Exception as e:
        print(f"Sync to sheets failed: {e}")

    return product


@app.put("/api/products/{product_id}")
async def update_product(product_id: int, request: Request):
    form = await request.form()
    name = form.get("name")
    regular_price = form.get("regular_price")
    description = form.get("description", "")

    if not name or not regular_price:
        raise HTTPException(status_code=400, detail="Name and regular_price are required")

    images = await get_images_from_form(form)
    images_value = ",".join(img["src"] for img in images)

    data = {
        "name": name,
        "regular_price": regular_price,
        "description": description,
        "images": [],
        "meta_data": [
            {"key": IMAGE_META_KEY, "value": images_value}
        ]
    }
    response = wcapi.put(f"products/{product_id}", data)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to update product: {response.text}"
        )

    product = response.json()
    inject_meta_images([product])

    try:
        sheets_sync.sync_from_woo_to_sheets(wcapi)
    except Exception as e:
        print(f"Sync to sheets failed: {e}")

    return product


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    response = wcapi.delete(f"products/{product_id}", params={"force": True})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to delete product")

    try:
        sheets_sync.sync_from_woo_to_sheets(wcapi)
    except Exception as e:
        print(f"Sync to sheets failed: {e}")

    return response.json()
