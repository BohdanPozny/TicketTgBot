from fastapi import APIRouter

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/success")
async def payment_success() -> dict:
    """
    Заглушка для обробки успішної оплати.
    У реальній системі тут обробляється webhook від платіжного провайдера.
    Telegram Payments обробляються безпосередньо у боті через successful_payment handler.
    """
    return {"ok": True, "message": "Payment processed via bot handler"}
