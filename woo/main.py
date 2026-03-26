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

print(f"Connecting to WooCommerce at: {WOO_URL}")

wcapi = API(
    url=WOO_URL,
    consumer_key=WOO_KEY,
    consumer_secret=WOO_SECRET,
    version="wc/v3",
    query_string_auth=True
)

@app.on_event("startup")
async def startup_event():
    print("Performing initial Google Sheets sync...")
    try:
        sheets_sync.full_sync(wcapi)
    except Exception as e:
        print(f"Initial sync failed: {e}")
        
    # Start background task for periodic sync
    asyncio.create_task(periodic_sync_task())

async def periodic_sync_task():
    while True:
        await asyncio.sleep(600)  # Every 10 minutes
        print("Performing periodic Google Sheets sync...")
        try:
            sheets_sync.full_sync(wcapi)
        except Exception as e:
            print(f"Periodic sync failed: {e}")

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/products")
async def get_products():
    response = wcapi.get("products")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch products")
    return response.json()

async def get_images_from_form(form):
    images = []
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
            # Ensure safe filename
            safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
            
            base_name, _ = os.path.splitext(safe_filename)
            final_filename = f"{base_name}.jpg"
            filepath = os.path.join("static", "uploads", final_filename)
            
            try:
                content = await file.read()
                img = Image.open(io.BytesIO(content))
                
                # Compress & Resize (max 1920x1920, keeps aspect ratio)
                img.thumbnail((1920, 1920))
                
                # Convert to RGB if format doesn't support transparency well or needs flat export
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                img.save(filepath, "JPEG", quality=80)
            except Exception as e:
                # Fallback to copy if PIL fails
                print(f"Image compression failed: {e}")
                final_filename = safe_filename
                filepath = os.path.join("static", "uploads", final_filename)
                await file.seek(0)
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                    
            images.append({"src": f"http://app:8000/static/uploads/{final_filename}"})
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
        
    data = {
        "name": name,
        "type": "simple",
        "regular_price": regular_price,
        "description": description,
        "images": images
    }
    response = wcapi.post("products", data)
    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to create product: {response.text}")
    
    # Sync to sheets
    try:
        sheets_sync.sync_from_woo_to_sheets(wcapi)
    except Exception as e:
        print(f"Sync to sheets failed: {e}")
        
    return response.json()

@app.put("/api/products/{product_id}")
async def update_product(product_id: int, request: Request):
    form = await request.form()
    name = form.get("name")
    regular_price = form.get("regular_price")
    description = form.get("description", "")
    
    if not name or not regular_price:
        raise HTTPException(status_code=400, detail="Name and regular_price are required")
        
    images = await get_images_from_form(form)
        
    data = {
        "name": name,
        "regular_price": regular_price,
        "description": description,
        "images": images
    }
    response = wcapi.put(f"products/{product_id}", data)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Failed to update product: {response.text}")
    
    # Sync to sheets
    try:
        sheets_sync.sync_from_woo_to_sheets(wcapi)
    except Exception as e:
        print(f"Sync to sheets failed: {e}")
        
    return response.json()

@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    response = wcapi.delete(f"products/{product_id}", params={"force": True})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to delete product")
    
    # Sync to sheets
    try:
        sheets_sync.sync_from_woo_to_sheets(wcapi)
    except Exception as e:
        print(f"Sync to sheets failed: {e}")
        
    return response.json()
