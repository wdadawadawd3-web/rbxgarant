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
    LabeledPrice
)
from aiogram.filters import Command

# ==========================================
# CONFIGURATION (Change these values)
# ==========================================
BOT_TOKEN = "8502294865:AAF7HAQ4B1GNG_-_15RJm0BCMBFvrEb476o"
WEBAPP_URL = "https://your-ngrok-url.ngrok-free.app"  # Must be HTTPS (e.g. Ngrok)
PORT = 8000
DB_PATH = "garant.db"

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
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 0
    )
    """)
    # Deals table
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
    clean_username = username.lower().replace("@", "")
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
            "seller_username_resolved": r[8]
        })
    return deals


# ==========================================
# TELEGRAM BOT HANDLERS (aiogram)
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Открыть WebApp", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        f"👋 Добро пожаловать в Roblox-стиль Гарант Бот!\n\n"
        f"🤖 Я помогу вам провести безопасную сделку в Telegram Stars ⭐️.\n\n"
        f"Нажмите кнопку ниже, чтобы открыть WebApp и управлять своим балансом и сделками.",
        reply_markup=kb
    )

# Telegram Stars Payment Handlers
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    stars = message.successful_payment.total_amount
    user_id = message.from_user.id
    
    # Save/Update user in database if they aren't registered yet
    save_user(user_id, message.from_user.username, message.from_user.first_name)
    
    # Credit user's balance
    update_user_balance(user_id, stars)
    
    await message.answer(
        f"🎉 Ваша оплата получена!\n"
        f"💰 На ваш баланс зачислено: *{stars}* ⭐️.\n"
        f"Вы можете проверить его, открыв WebApp."
    )

# Callback queries for deal actions
@dp.callback_query(F.data.startswith("deal_accept:"))
async def handle_deal_accept(callback_query: CallbackQuery):
    deal_id = callback_query.data.split(":")[1]
    deal = get_deal_record(deal_id)
    
    if not deal:
        await callback_query.answer("Сделка не найдена.", show_alert=True)
        return
    
    if callback_query.from_user.id != deal["seller_id"]:
        await callback_query.answer("Вы не являетесь продавцом в этой сделке!", show_alert=True)
        return
        
    if deal["status"] != "created":
        await callback_query.answer(f"Сделка уже находится в статусе: {deal['status']}", show_alert=True)
        return
        
    update_deal_status(deal_id, "active")
    
    # Edit the seller's message
    await callback_query.message.edit_text(
        f"✅ *Вы приняли сделку {deal_id}!*\n\n"
        f"📦 *Товар:* {deal['description']}\n"
        f"💰 *Сумма:* {deal['amount']} ⭐️\n\n"
        f"Пожалуйста, передайте товар покупателю. После получения товара покупатель должен подтвердить выполнение в WebApp.",
        reply_markup=None,
        parse_mode="Markdown"
    )
    
    # Notify buyer
    try:
        await bot.send_message(
            deal["buyer_id"],
            f"🎉 Продавец принял вашу сделку *{deal_id}*!\n"
            f"📦 Ожидайте передачу товара: *{deal['description']}*.\n"
            f"После получения подтвердите выполнение сделки в WebApp.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify buyer: {e}")

@dp.callback_query(F.data.startswith("deal_decline:"))
async def handle_deal_decline(callback_query: CallbackQuery):
    deal_id = callback_query.data.split(":")[1]
    deal = get_deal_record(deal_id)
    
    if not deal:
        await callback_query.answer("Сделка не найдена.", show_alert=True)
        return
    
    # Either buyer or seller can decline/cancel a pending deal
    user_id = callback_query.from_user.id
    if user_id != deal["seller_id"] and user_id != deal["buyer_id"]:
        await callback_query.answer("Вы не являетесь участником этой сделки!", show_alert=True)
        return
        
    if deal["status"] != "created":
        await callback_query.answer(f"Сделка уже находится в статусе: {deal['status']}", show_alert=True)
        return
        
    update_deal_status(deal_id, "declined")
    
    # Refund buyer ONLY if they already paid (i.e., if the seller is the one declining)
    was_paid = (user_id == deal["seller_id"])
    if was_paid:
        update_user_balance(deal["buyer_id"], deal["amount"])
        refund_text = "\n💰 Средства возвращены на баланс покупателя."
    else:
        refund_text = ""
    
    # Edit the message
    await callback_query.message.edit_text(
        f"❌ *Сделка {deal_id} отклонена.*{refund_text}",
        reply_markup=None,
        parse_mode="Markdown"
    )
    
    # Notify the other party
    other_party_id = deal["buyer_id"] if user_id == deal["seller_id"] else deal["seller_id"]
    try:
        await bot.send_message(
            other_party_id,
            f"❌ Участник отклонил сделку *{deal_id}*."
            + (f"\n💰 Сумма *{deal['amount']}* ⭐️ возвращена на ваш баланс." if was_paid else ""),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify other party: {e}")

@dp.callback_query(F.data.startswith("deal_pay_accept:"))
async def handle_deal_pay_accept(callback_query: CallbackQuery):
    deal_id = callback_query.data.split(":")[1]
    deal = get_deal_record(deal_id)
    
    if not deal:
        await callback_query.answer("Сделка не найдена.", show_alert=True)
        return
        
    if callback_query.from_user.id != deal["buyer_id"]:
        await callback_query.answer("Вы не являетесь покупателем в этой сделке!", show_alert=True)
        return
        
    if deal["status"] != "created":
        await callback_query.answer(f"Сделка уже находится в статусе: {deal['status']}", show_alert=True)
        return
        
    # Check buyer balance
    buyer = get_user_by_id(deal["buyer_id"])
    if not buyer or buyer["balance"] < deal["amount"]:
        await callback_query.answer(
            "❌ Недостаточно Stars на вашем балансе! Пожалуйста, пополните баланс в WebApp.", 
            show_alert=True
        )
        return
        
    # Deduct balance (freeze)
    update_user_balance(deal["buyer_id"], -deal["amount"])
    
    # Update status to active
    update_deal_status(deal_id, "active")
    
    # Edit buyer's message
    await callback_query.message.edit_text(
        f"✅ *Вы оплатили и приняли сделку {deal_id}!*\n\n"
        f"📦 *Товар:* {deal['description']}\n"
        f"💰 *Списано:* {deal['amount']} ⭐️\n\n"
        f"Ожидайте передачу товара от продавца. После получения подтвердите выполнение сделки в WebApp.",
        reply_markup=None,
        parse_mode="Markdown"
    )
    
    # Notify seller
    try:
        await bot.send_message(
            deal["seller_id"],
            f"🎉 Покупатель оплатил и принял сделку *{deal_id}*!\n"
            f"📦 Пожалуйста, передайте ему товар: *{deal['description']}*.\n"
            f"После передачи покупатель подтвердит получение товара в WebApp.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify seller: {e}")



# ==========================================
# FASTAPI SECURITY (InitData Verification)
# ==========================================
def verify_init_data(init_data: str) -> Optional[dict]:
    """
    Verifies the integrity of data received from the Telegram WebApp.
    Returns the parsed user dictionary if valid, or None.
    """
    try:
        parsed = parse_qs(init_data)
        if "hash" not in parsed:
            return None
        received_hash = parsed["hash"][0]
        
        # Sort key-value pairs alphabetically
        sorted_items = sorted([(k, v[0]) for k, v in parsed.items() if k != "hash"])
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted_items])
        
        # Calculate signature
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == received_hash:
            # Parse user data
            user_data = json.loads(parsed["user"][0])
            return user_data
    except Exception as e:
        logger.error(f"Error verifying Telegram WebApp initData: {e}")
    return None


# ==========================================
# FASTAPI BACKEND (Endpoints & Setup)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    init_db()
    
    # Start bot polling in background
    polling_task = asyncio.create_task(dp.start_polling(bot))
    logger.info("Bot polling started.")
    
    yield
    
    # Shutdown
    await dp.stop_polling()
    await bot.session.close()
    polling_task.cancel()
    logger.info("Bot and server shutdown complete.")

app = FastAPI(lifespan=lifespan)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class DepositRequest(BaseModel):
    amount: int

class DealRequest(BaseModel):
    seller_username: str
    amount: int
    description: str

class DealRequest(BaseModel):
    partner_username: str
    amount: int
    description: str
    creator_role: str  # "buyer" or "seller"

class DealActionRequest(BaseModel):
    deal_id: str

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def get_index():
    if not os.path.exists("index.html"):
        return "<h3>index.html not found. Please create the frontend file.</h3>"
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/api/profile")
async def get_profile(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_data = verify_init_data(authorization)
    if not user_data:
        raise HTTPException(status_code=403, detail="Invalid credentials")
        
    user_id = user_data["id"]
    username = user_data.get("username")
    first_name = user_data.get("first_name", "Player")
    
    # Save user details to DB
    save_user(user_id, username, first_name)
    
    # Get profile details
    user = get_user_by_id(user_id)
    deals = get_user_deals_list(user_id)
    
    return {
        "user": user,
        "deals": deals
    }

@app.post("/api/create_deposit")
async def create_deposit(req: DepositRequest, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_data = verify_init_data(authorization)
    if not user_data:
        raise HTTPException(status_code=403, detail="Invalid credentials")
        
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
        
    # Generate Stars Invoice Link
    try:
        invoice_link = await bot.create_invoice_link(
            title="Пополнение баланса",
            description=f"Пополнение баланса в боте-гаранте на {req.amount} Stars",
            payload="stars_deposit",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=req.amount)]
        )
        return {"invoice_link": invoice_link}
    except Exception as e:
        logger.error(f"Failed to create invoice link: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate payment link")

@app.post("/api/create_deal")
async def create_deal(req: DealRequest, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_data = verify_init_data(authorization)
    if not user_data:
        raise HTTPException(status_code=403, detail="Invalid credentials")
        
    creator_id = user_data["id"]
    creator_username = user_data.get("username", "User")
    
    # Resolve the second participant
    partner = get_user_by_username(req.partner_username)
    if not partner:
        return JSONResponse(
            status_code=400, 
            content={"error": "Второй участник не найден в боте. Он должен сначала запустить бота!"}
        )
        
    if partner["id"] == creator_id:
        return JSONResponse(status_code=400, content={"error": "Нельзя проводить сделку с самим собой!"})
        
    deal_id = f"DX-{os.urandom(2).hex().upper()}"
    
    if req.creator_role == "buyer":
        # Current user is BUYER, partner is SELLER
        buyer_id = creator_id
        seller_id = partner["id"]
        
        # Check buyer balance
        buyer = get_user_by_id(buyer_id)
        if not buyer or buyer["balance"] < req.amount:
            return JSONResponse(status_code=400, content={"error": "Недостаточно Stars на вашем балансе"})
            
        # Deduct balance (freeze)
        update_user_balance(buyer_id, -req.amount)
        
        # Save deal
        create_deal_record(deal_id, buyer_id, seller_id, req.partner_username, req.amount, req.description)
        
        # Send message to seller
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Принять ✅", callback_data=f"deal_accept:{deal_id}"),
                InlineKeyboardButton(text="Отклонить ❌", callback_data=f"deal_decline:{deal_id}")
            ]
        ])
        
        try:
            await bot.send_message(
                seller_id,
                f"👋 *Новая сделка {deal_id}!*\n\n"
                f"👤 *Покупатель:* @{creator_username}\n"
                f"📦 *Товар:* {req.description}\n"
                f"💰 *Сумма:* {req.amount} ⭐️\n\n"
                f"Вы согласны выступить продавцом в этой сделке?",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            update_user_balance(buyer_id, req.amount) # rollback
            return JSONResponse(status_code=500, content={"error": "Не удалось уведомить продавца"})
            
    else:
        # Current user is SELLER, partner is BUYER
        buyer_id = partner["id"]
        seller_id = creator_id
        
        # Save deal (starts as 'created', waiting for buyer to pay)
        create_deal_record(deal_id, buyer_id, seller_id, creator_username, req.amount, req.description)
        
        # Send message to buyer to pay and accept
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Оплатить и принять 💳", callback_data=f"deal_pay_accept:{deal_id}"),
                InlineKeyboardButton(text="Отклонить ❌", callback_data=f"deal_decline:{deal_id}")
            ]
        ])
        
        try:
            await bot.send_message(
                buyer_id,
                f"👋 *Предложение сделки {deal_id}!*\n\n"
                f"👤 *Продавец:* @{creator_username}\n"
                f"📦 *Товар:* {req.description}\n"
                f"💰 *Стоимость:* {req.amount} ⭐️\n\n"
                f"Вы согласны оплатить и принять эту сделку?",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            update_deal_status(deal_id, "failed")
            return JSONResponse(status_code=500, content={"error": "Не удалось уведомить покупателя"})
            
    return {"success": True, "deal_id": deal_id}

@app.post("/api/confirm_deal")
async def confirm_deal(req: DealActionRequest, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_data = verify_init_data(authorization)
    if not user_data:
        raise HTTPException(status_code=403, detail="Invalid credentials")
        
    buyer_id = user_data["id"]
    deal = get_deal_record(req.deal_id)
    
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
        
    if deal["buyer_id"] != buyer_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
        
    if deal["status"] != "active":
        raise HTTPException(status_code=400, detail="Сделка не в активном статусе")
        
    # Update status to completed
    update_deal_status(req.deal_id, "completed")
    
    # Transfer stars to seller
    update_user_balance(deal["seller_id"], deal["amount"])
    
    # Notify both parties
    try:
        # Notify seller
        await bot.send_message(
            deal["seller_id"],
            f"🎉 *Сделка {req.deal_id} завершена!*\n"
            f"Покупатель подтвердил получение товара.\n"
            f"💰 На ваш баланс начислено: *{deal['amount']}* ⭐️.",
            parse_mode="Markdown"
        )
        # Notify buyer
        await bot.send_message(
            deal["buyer_id"],
            f"🎉 *Сделка {req.deal_id} завершена!*\n"
            f"Вы подтвердили получение товара. Средства переведены продавцу.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Notification error: {e}")
        
    return {"success": True}

@app.post("/api/dispute_deal")
async def dispute_deal(req: DealActionRequest, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_data = verify_init_data(authorization)
    if not user_data:
        raise HTTPException(status_code=403, detail="Invalid credentials")
        
    user_id = user_data["id"]
    deal = get_deal_record(req.deal_id)
    
    if not deal:
        raise HTTPException(status_code=404, detail="Сделка не найдена")
        
    if deal["buyer_id"] != user_id and deal["seller_id"] != user_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
        
    if deal["status"] != "active":
        raise HTTPException(status_code=400, detail="Сделка не в активном статусе")
        
    # Update status to disputed
    update_deal_status(req.deal_id, "disputed")
    
    # Notify both
    try:
        msg = (
            f"⚠️ *Открыт арбитраж по сделке {req.deal_id}!*\n"
            f"Сделка приостановлена. В ближайшее время администратор подключится для разбора ситуации."
        )
        await bot.send_message(deal["buyer_id"], msg, parse_mode="Markdown")
        await bot.send_message(deal["seller_id"], msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Notification error: {e}")
        
    return {"success": True}

# ==========================================
# RUN APPLICATION
# ==========================================
if __name__ == "__main__":
    import uvicorn
    # Check if Bot Token is provided
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your BOT_TOKEN in server.py!")
        exit(1)
    
    print(f"🚀 Starting FastAPI server on port {PORT}...")
    print(f"🔗 Make sure to set your WebApp URL to {WEBAPP_URL} in Telegram BotFather!")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
