from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, users, profile, products, oauth, categories, subcategories, orders, alias, invoice, lava, gifts
from log_notifier import exception_handler
from utils import scheduler, IS_TEST

if IS_TEST:
    app = FastAPI(docs_url="/api/docs")
    cors_origins = ["*"]

else:
    app = FastAPI()
    app.add_exception_handler(Exception, exception_handler)

    allow_origins = ["gamemoneta.com", "pay.gamemoneta.com",
                     "81.177.135.164", "90.189.147.33", "147.30.70.48", "195.161.68.242",
                     "62.122.172.72", "62.122.173.38", "91.227.144.73"]  # LAVA ip-адреса


    @app.middleware("http")
    async def restrict_to_frontend(request: Request, call_next):
        origin = request.headers.get("origin", "").split("://")[-1]
        referer = request.headers.get("referer", "").split("://")[-1]

        if origin and origin not in allow_origins or referer and not any(
                referer.startswith(allowed) for allowed in allow_origins):
            return JSONResponse(
                status_code=401,
                content={"detail": f"Unauthorized request from third-party: {referer or origin}"},
            )

        return await call_next(request)


    cors_origins = ["https://gamemoneta.com", "https://pay.gamemoneta.com",
                    "http://81.177.135.164", "http://90.189.147.33", "http://147.30.70.48", "http://195.161.68.242",
                    "http://62.122.172.72", "http://62.122.173.38", "http://91.227.144.73"] # LAVA ip-адреса

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(users.router, prefix="/api/users")
app.include_router(profile.router, prefix="/api/profile")
app.include_router(products.router, prefix="/api/products")
app.include_router(oauth.router, prefix="/api/oauth")
app.include_router(categories.router, prefix="/api/categories")
app.include_router(subcategories.router, prefix="/api/subcategories")
app.include_router(orders.router, prefix="/api/orders")
app.include_router(alias.router, prefix="/api/alias")
app.include_router(invoice.router, prefix="/api/invoice")
app.include_router(lava.router, prefix="/api/lava")
app.include_router(gifts.router, prefix="/api/gifts")

tags_metadata = [
    {
        "name": "Auth",
        "description": "Manage authorization. Check _utils.py_ for JWT details.",
    },
    {
        "name": "Users",
        "description": "Manage users.",
    },
    {
        "name": "Profile",
        "description": "Manage users' credentials and details.",
    },
    {
        "name": "Products",
        "description": "Manage products.",
    },
    {
        "name": "OAuth",
        "description": "Operations with OAuth (Telegram, VK, etc.).",
    },
    {
        "name": "Telegram",
    },
    {
        "name": "Categories",
        "description": "Manage categories.",
    },
    {
        "name": "Subcategories",
        "description": "Manage subcategories.",
    },
    {
        "name": "Orders",
        "description": "Manage orders.",
    },
    {
        "name": "Invoices",
        "description": "Manage invoices.",
    },
    {
        "name": "LAVA",
        "description": "Manage LAVA invoices.",
    },
]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


    @app.on_event("shutdown")
    def shutdown_event():
        scheduler.shutdown()
