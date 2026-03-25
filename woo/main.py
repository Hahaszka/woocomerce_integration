import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from woocommerce import API

app = FastAPI()

templates = Jinja2Templates(directory="templates")

WOO_URL = os.getenv("WOO_URL", "http://wordpress")
WOO_KEY = os.getenv("WOO_KEY", "ck_placeholder_key")
WOO_SECRET = os.getenv("WOO_SECRET", "cs_placeholder_secret")

print(f"Connecting to WooCommerce at: {WOO_URL}")

# Use index.php and query_string_auth to avoid 301 redirects in Docker network
wcapi = API(
    url=WOO_URL,
    consumer_key=WOO_KEY,
    consumer_secret=WOO_SECRET,
    version="wc/v3",
    query_string_auth=True
)

# Overriding the API's products endpoint to use non-pretty permalinks if necessary
# but the easiest way is to just use the library's default and ensure no 301.
# If 301 still occurs, we will use index.php in the url.


class ProductImage(BaseModel):
    src: str

class ProductCreate(BaseModel):
    name: str
    regular_price: str
    images: Optional[List[ProductImage]] = None

class ProductUpdate(BaseModel):
    name: str
    regular_price: str
    images: Optional[List[ProductImage]] = None

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/products")
async def get_products():
    response = wcapi.get("products")
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch products")
    return response.json()

@app.post("/api/products")
async def create_product(product: ProductCreate):
    data = {
        "name": product.name,
        "type": "simple",
        "regular_price": product.regular_price,
        "images": [img.dict() for img in product.images] if product.images else []
    }
    response = wcapi.post("products", data)
    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=response.status_code, detail="Failed to create product")
    return response.json()

@app.put("/api/products/{product_id}")
async def update_product(product_id: int, product: ProductUpdate):
    data = {
        "name": product.name,
        "regular_price": product.regular_price,
        "images": [img.dict() for img in product.images] if product.images else []
    }
    response = wcapi.put(f"products/{product_id}", data)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to update product")
    return response.json()

@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    response = wcapi.delete(f"products/{product_id}", params={"force": True})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to delete product")
    return response.json()
