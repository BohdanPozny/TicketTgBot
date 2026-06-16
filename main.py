import asyncio
from contextlib import asynccontextmanager
from contextlib import suppress

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.miniapp import router as miniapp_router
from api.payments import router as payments_router
from api.tickets import router as tickets_router
from api.webhooks import router as webhook_router
from bot.loader import bot, setup_routers
from core.config import settings
from database.db_setup import create_tables
from services.verification_service import VerificationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_routers()
    if settings.database_auto_create_tables:
        await create_tables()
    await _seed_categories()
    verification_task = asyncio.create_task(_expire_verifications_loop())

    if settings.webhook_url:
        await bot.set_webhook(
            url=settings.full_webhook_url,
            allowed_updates=["message", "callback_query", "web_app_data"],
            drop_pending_updates=True,
        )

    yield

    verification_task.cancel()
    with suppress(asyncio.CancelledError):
        await verification_task

    if settings.webhook_url:
        await bot.delete_webhook()
    await bot.session.close()


async def _seed_categories():
    from database.db_setup import async_session_factory
    from database.repositories.events import EventRepository

    async with async_session_factory() as session:
        repo = EventRepository(session)
        categories = await repo.get_all_categories()
        if not categories:
            await repo.create_category("Кіно", "cinema", "🎬")
            await repo.create_category("Автобуси", "bus", "🚌")
            await session.commit()


async def _expire_verifications_loop() -> None:
    from database.db_setup import async_session_factory

    while True:
        await asyncio.sleep(30)
        async with async_session_factory() as session:
            service = VerificationService(session)
            await service.expire_stale_verifications()
            await session.commit()


app = FastAPI(
    title="TicketTgBot API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ([settings.webhook_url] if settings.webhook_url else []),
    allow_credentials=bool(settings.cors_origins or settings.webhook_url),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(webhook_router)
app.include_router(miniapp_router)
app.include_router(tickets_router)
app.include_router(payments_router)


@app.get("/miniapp/cinema/customer", response_class=HTMLResponse)
async def cinema_customer_app(request: Request, event_id: int):
    return templates.TemplateResponse(
        "categories/cinema/customer.html",
        {"request": request, "event_id": event_id, "api_base": settings.webhook_url},
    )


@app.get("/miniapp/cinema/partner", response_class=HTMLResponse)
async def cinema_partner_app(request: Request, event_id: int):
    return templates.TemplateResponse(
        "categories/cinema/partner.html",
        {"request": request, "event_id": event_id, "api_base": settings.webhook_url},
    )


@app.get("/miniapp/bus/customer", response_class=HTMLResponse)
async def bus_customer_app(request: Request, event_id: int):
    return templates.TemplateResponse(
        "categories/bus/customer.html",
        {"request": request, "event_id": event_id, "api_base": settings.webhook_url},
    )


@app.get("/miniapp/bus/partner", response_class=HTMLResponse)
async def bus_partner_app(request: Request, event_id: int):
    return templates.TemplateResponse(
        "categories/bus/partner.html",
        {"request": request, "event_id": event_id, "api_base": settings.webhook_url},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
