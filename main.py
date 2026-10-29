import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers import (
    cart,
    health,
    order,
    payment,
    product,
    restore_password,
    user_auth,
    user_registration,
)

app = FastAPI(title="E-commerce of legumes", version="1.0.0")

media_root = Path(os.getenv("MEDIA_ROOT", "media")).resolve()
media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_root), name="media")

app.include_router(payment.router)
app.include_router(product.router)
app.include_router(cart.router)
app.include_router(order.router)
app.include_router(health.router)
app.include_router(user_registration.router)
app.include_router(user_auth.router_login)
app.include_router(user_auth.router_home_page)
app.include_router(restore_password.router)
