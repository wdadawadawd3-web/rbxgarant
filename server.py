import os
import json
import hmac
import hashlib
import sqlite3
import logging
import asyncio
from typing import Optional
from urllib.parse import parse_qs
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, 
    CallbackQuery, 
    PreCheckoutQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    WebAppInfo,
    LabeledPrice,
    Update
)
from aiogram.filters import Command

# Переходник для асинхронного FastAPI на синхронном PythonAnywhere
from a2wsgi import ASGIMiddleware

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8502294865:AAF7HAQ4B1GNG_-_15RJm0BCMBFvrEb476o"
WEBAPP_URL = "https://robopo1.pythonanywhere.com"  # ТВОЙ АДРЕС НА PYTHONANYWHERE
PORT = 8000
DB_PATH = os.path.join(os.path.dirname(__file__), "garant.db")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# DATABASE HELPERS (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deals (
        id TEXT PRIMARY KEY,
        buyer_id INTEGER,
        seller_id INTEGER,
        seller_username TEXT,
        amount INTEGER,
        description TEXT,
        status TEXT,
        FOREIGN KEY(buyer_id) REFERENCES users(id),
        FOREIGN KEY(seller_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def save_user(user_id: int, username: Optional[str], first_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_username = username.lower().replace("@", "") if username else None
    cursor.execute("""
    INSERT INTO users (id, username, first_name)
    VALUES (?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        username = excluded.username,
        first_name = excluded.first_name
    """, (user_id, clean_username, first_name))
    conn.commit()
    conn.close()

def get_user_by_id(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, first_name, balance FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "first_name": row[2], "balance": row[3]}
    return None

def get_user_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_username = username.lower().replace("@", "").strip()
    cursor.execute("SELECT id, username, first_name, balance FROM users WHERE username = ?", (clean_username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "first_name": row[2], "balance": row[3]}
    return None

def update_user_balance(user_id: int, amount_change: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount_change, user_id))
    conn.commit()
    conn.close()

def create_deal_record(deal_id: str, buyer_id: int, seller_id: int, seller_username: str, amount: int, description: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO deals (id, buyer_id, seller_id, seller_username, amount, description, status)
    VALUES (?, ?, ?, ?, ?, ?, 'created')
    """, (deal_id, buyer_id, seller_id, seller_username, amount, description))
    conn.commit()
    conn.close()

def get_deal_record(deal_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, buyer_id, seller_id, seller_username, amount, description, status FROM deals WHERE id = ?", (deal_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "buyer_id": row[1],
            "seller_id": row[2],
            "seller_username": row[3],
            "amount": row[4],
            "description": row[5],
            "status": row[6]
        }
    return None

def update_deal_status(deal_id: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET status = ? WHERE id = ?", (status, deal_id))
    conn.commit()
    conn.close()

def get_user_deals_list(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT d.id, d.buyer_id, d.seller_id, d.seller_username, d.amount, d.description, d.status,
           u1.username as buyer_username, u2.username as seller_username_resolved
    FROM deals d
    LEFT JOIN users u1 ON d.buyer_id = u1.id
    LEFT JOIN users u2 ON d.seller_id = u2.id
    WHERE d.buyer_id = ? OR d.seller_id = ?
    ORDER BY d.rowid DESC
    """, (user_id, user_id))
    rows = cursor.fetchall()
    conn.close()
    
    deals = []
    for r in rows:
        deals.append({
            "id": r[0],
            "buyer_id": r[1],
            "seller_id": r[2],
            "seller_username": r[3],
            "amount": r[4],
            "description": r[5],
            "status": r[6],
            "buyer_username": r[7],
            "seller_username_resolved": r[8],
            "status_text": "Активна" if r[6] == "active" else "Завершена" if r[6] == "completed" else "Ожидает"
        })
    return deals


# ==========================================
# TELEGRAM BOT HANDLERS (aiogram)
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    # URL твоего фронтенда на Vercel!
    VERCEL_URL = "https://rbxgarant.vercel.app" # Укажи здесь свою ссылку от Vercel, если она отличается
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Открыть WebApp", web_app=WebAppInfo(url=VERCEL_URL))]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"👋 Добро пожаловать в Roblox Гарант Бот!\n\n"
        f"🤖 Безопасные сделки в Telegram Stars ⭐️.\n\n"
        f"Нажмите кнопку ниже, чтобы войти в интерфейс гаранта.",
        reply_markup=kb
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    stars = message.successful_payment.total_amount
    user_id = message.from_user.id
    save_user(user_id, message.from_user.username, message.from_user.first_name)
    update_user_balance(user_id, stars)
    await message.answer(f"🎉 Зачислено: *{stars}* ⭐️.\nПроверьте баланс в WebApp.")

# Callback-обработчики кнопок сделок в чате
@dp.callback_query(F.data.startswith("deal_accept:"))
async def handle_deal_accept(callback_query: CallbackQuery):
    deal_id = callback_query.data.split(":")[1]
    deal = get_deal_record(deal_id)
    if not deal or callback_query.from_user.id != deal["seller_id"] or deal["status"] != "created":
        await callback_query.answer("Ошибка или сделка уже активна.", show_alert=True)
        return
    update_deal_status(deal_id, "active")
    await callback_query.message.edit_text(f"✅ *Вы приняли сделку {deal_id}!* Передайте товар.", reply_markup=None, parse_mode="Markdown")
    try:
        await bot.send_message(deal["buyer_id"], f"🎉 Продавец принял вашу сделку *{deal_id}*! Подтвердите получение в WebApp после передачи.")
    except Exception: pass

@dp.callback_query(F.data.startswith("deal_decline:"))
async def handle_deal_decline(callback_query: CallbackQuery):
    deal_id = callback_query.data.split(":")[1]
    deal = get_deal_record(deal_id)
    if not deal or deal["status"] != "created": return
    update_deal_status(deal_id, "declined")
    if callback_query.from_user.id == deal["seller_id"]:
        update_user_balance(deal["buyer_id"], deal["amount"])
    await callback_query.message.edit_text(f"❌ *Сделка {deal_id} отклонена.*", reply_markup=None, parse_mode="Markdown")


# ==========================================
# FASTAPI SECURITY (InitData Verification)
# ==========================================
def verify_init_data(init_data: str) -> Optional[dict]:
    try:
        parsed = parse_qs(init_data)
        if "hash" not in parsed: return None
        received_hash = parsed["hash"][0]
        sorted_items = sorted([(k, v[0]) for k, v in parsed.items() if k != "hash"])
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_items])
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash == received_hash:
            return json.loads(parsed["user"][0])
    except Exception: pass
    return None


# ==========================================
# FASTAPI BACKEND
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        update_dict = await request.json()
        update = Update.model_validate(update_dict, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        return JSONResponse(status_code=500, content={"status": "error"})
    return {"ok": True}

# Request Models
class DepositRequest(BaseModel):
    amount: int
    user_id: Optional[int] = None

class DealRequest(BaseModel):
    partner: str
    amount: int
    item: str

class DealActionRequest(BaseModel):
    deal_id: str

@app.get("/api/user/{user_id}")
async def get_user_profile(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        return {"balance": 0, "deals": []}
    deals = get_user_deals_list(user_id)
    return {"balance": user["balance"], "deals": deals}

@app.post("/api/deposit")
async def create_deposit(req: DepositRequest):
    if req.amount <= 0: raise HTTPException(status_code=400, detail="Invalid amount")
    try:
        invoice_link = await bot.create_invoice_link(
            title="Пополнение баланса",
            description=f"Пополнение баланса на {req.amount} Stars",
            payload="stars_deposit",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=req.amount)]
        )
        if req.user_id:
            await bot.send_invoice(
                chat_id=req.user_id,
                title="Пополнение баланса",
                description=f"Счет на {req.amount} Stars",
                payload="stars_deposit",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Stars", amount=req.amount)]
            )
        return {"invoice_link": invoice_link}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate payment link")

@app.post("/api/deals/create")
async def create_deal(req: DealRequest, authorization: str = Header(None)):
    if not authorization: raise HTTPException(status_code=401)
    user_data = verify_init_data(authorization)
    if not user_data: raise HTTPException(status_code=403)
    
    buyer_id = user_data["id"]
    buyer_name = user_data.get("username", "Buyer")
    
    partner_username = req.partner.replace("@", "").strip()
    partner = get_user_by_username(partner_username)
    if not partner:
        return JSONResponse(status_code=400, content={"detail": "Второй участник должен сначала запустить бота!"})
        
    seller_id = partner["id"]
    deal_id = f"DX-{os.urandom(2).hex().upper()}"
    
    update_user_balance(buyer_id, -req.amount)
    create_deal_record(deal_id, buyer_id, seller_id, partner_username, req.amount, req.item)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Принять ✅", callback_data=f"deal_accept:{deal_id}"),
            InlineKeyboardButton(text="Отклонить ❌", callback_data=f"deal_decline:{deal_id}")
        ]
    ])
    try:
        await bot.send_message(
            seller_id,
            f"👋 *Новая сделка {deal_id}!*\n\n👤 *Покупатель:* @{buyer_name}\n📦 *Товар:* {req.item}\n💰 *Сумма:* {req.amount} ⭐️\n\nВы согласны выступить продавцом?",
            reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception: pass
    return {"success": True}

# Превращаем асинхронный FastAPI в понятную для PythonAnywhere переменную WSGI
wsgi_app = ASGIMiddleware(app)
