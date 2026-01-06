# 1. Установите библиотеку: pip install aiogram
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# 2. Вставьте ваш токен
BOT_TOKEN = "8318435259:AAGWFqs9k715u1SwXgUx3PiZ_MKDxkVz9mk"

# 3. Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 4. Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот. Рад познакомиться!")

# 5. Обработчик обычных текстовых сообщений
@dp.message()
async def echo_message(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

# 6. Главная функция для запуска
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())