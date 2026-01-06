# bot_schedule25_fixed.py
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "8318435259:AAGWFqs9k715u1SwXgUx3PiZ_MKDxkVz9mk")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM состояния
class Form(StatesGroup):
    waiting_for_class = State()
    waiting_for_day = State()

# Кэш для расписания
schedule_cache = {
    'data': None,
    'timestamp': None,
    'ttl': timedelta(minutes=30)
}

# Дни недели на русском
RUS_WEEKDAYS = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']

async def fetch_schedule() -> Dict:
    """Получаем расписание с сайта"""
    url = "http://www.dnevnik25.ru/расписание.htm"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    return await parse_complex_schedule(html)
                else:
                    logger.error(f"Ошибка HTTP: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        return {}

async def parse_complex_schedule(html: str) -> Dict:
    """Парсим сложную структуру таблицы"""
    soup = BeautifulSoup(html, 'lxml')
    schedule_data = {}
    
    # Находим все заголовки с днями недели
    day_elements = soup.find_all(['h2', 'h3', 'h4', 'p', 'b', 'strong'])
    
    for element in day_elements:
        text = element.get_text(strip=True, separator=' ').lower()
        
        # Проверяем, содержит ли элемент день недели
        day_found = None
        for day in RUS_WEEKDAYS:
            if day in text:
                day_found = day
                break
        
        if day_found:
            logger.info(f"Найден день недели: {day_found}")
            
            # Ищем таблицу после заголовка
            table = element.find_next('table')
            
            if table:
                day_schedule = await parse_day_table(table, day_found)
                if day_schedule:
                    # Объединяем с существующими данными
                    for class_name, lessons in day_schedule.items():
                        if class_name not in schedule_data:
                            schedule_data[class_name] = {}
                        if day_found not in schedule_data[class_name]:
                            schedule_data[class_name][day_found] = {}
                        
                        schedule_data[class_name][day_found].update(lessons)
    
    return schedule_data

async def parse_day_table(table, day: str) -> Dict:
    """Парсим таблицу одного дня"""
    schedule = {}
    
    # Получаем все строки таблицы
    rows = table.find_all('tr')
    if len(rows) < 3:
        return {}
    
    # Шаг 1: Определяем колонки с классами
    header_row = None
    for i, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        if len(cells) > 10:  # Ищем строку с многими колонками (скорее всего заголовок)
            header_row = i
            break
    
    if header_row is None:
        return {}
    
    # Получаем названия классов из заголовка
    header_cells = rows[header_row].find_all(['td', 'th'])
    classes = []
    
    for cell in header_cells:
        text = cell.get_text(strip=True)
        # Проверяем, похоже ли на название класса (5А, 10Б и т.д.)
        if re.match(r'^\d+[А-Я]?$', text):
            classes.append(text)
    
    if not classes:
        # Попробуем альтернативный способ
        classes = await extract_classes_from_table(table)
    
    # Шаг 2: Парсим строки с уроками
    current_lesson = None
    current_time = None
    
    for i in range(header_row + 1, len(rows)):
        row = rows[i]
        cells = row.find_all(['td', 'th'])
        
        if not cells:
            continue
        
        # Первая ячейка может содержать номер урока или время
        first_cell = cells[0].get_text(strip=True)
        
        # Проверяем, является ли это номером урока (цифра 1-8)
        if first_cell.isdigit() and 1 <= int(first_cell) <= 8:
            current_lesson = int(first_cell)
            
            # Вторая ячейка может содержать время
            if len(cells) > 1:
                time_text = cells[1].get_text(strip=True)
                if '–' in time_text or '-' in time_text or ':' in time_text:
                    current_time = time_text
                else:
                    # Ищем время в следующей строке
                    if i + 1 < len(rows):
                        next_cells = rows[i + 1].find_all(['td', 'th'])
                        if len(next_cells) > 1:
                            time_text = next_cells[1].get_text(strip=True)
                            if '–' in time_text or '-' in time_text or ':' in time_text:
                                current_time = time_text
        
        # Если у нас есть номер урока и время, парсим остальные ячейки
        if current_lesson and current_time:
            for j, cell in enumerate(cells[2:], start=2):  # Пропускаем первые 2 колонки (номер и время)
                if j - 2 < len(classes):  # Проверяем, что есть соответствующий класс
                    class_name = classes[j - 2]
                    cell_text = cell.get_text(strip=True)
                    
                    if cell_text and cell_text not in ['', ' ', '  ']:
                        # Сохраняем полный текст ячейки
                        if class_name not in schedule:
                            schedule[class_name] = {}
                        
                        lesson_key = f"{current_lesson}_{current_time}"
                        schedule[class_name][lesson_key] = cell_text
    
    return schedule

async def extract_classes_from_table(table) -> List[str]:
    """Извлекаем названия классов из таблицы"""
    classes = []
    
    # Ищем все ячейки в таблице
    cells = table.find_all(['td', 'th'])
    
    for cell in cells:
        text = cell.get_text(strip=True)
        # Ищем паттерны классов: 5А, 10Б, 11М и т.д.
        matches = re.findall(r'\b(\d+[А-Я]?)\b', text)
        for match in matches:
            if match not in classes:
                classes.append(match)
    
    return classes

async def get_cached_schedule() -> Dict:
    """Получаем расписание с кэшированием"""
    now = datetime.now()
    
    if (schedule_cache['data'] is None or 
        schedule_cache['timestamp'] is None or
        now - schedule_cache['timestamp'] > schedule_cache['ttl']):
        
        logger.info("Обновляем кэш расписания...")
        schedule_cache['data'] = await fetch_schedule()
        schedule_cache['timestamp'] = now
    
    return schedule_cache['data']

async def get_available_classes() -> List[str]:
    """Получаем список доступных классов"""
    schedule_data = await get_cached_schedule()
    return list(schedule_data.keys())

async def format_schedule_for_class_day(class_name: str, day: str) -> str:
    """Форматируем расписание для конкретного класса и дня"""
    schedule_data = await get_cached_schedule()
    
    if class_name not in schedule_data:
        return f"❌ Класс {class_name} не найден в расписании"
    
    class_data = schedule_data[class_name]
    
    if day not in class_data:
        return f"❌ Нет расписания на {day} для класса {class_name}"
    
    day_schedule = class_data[day]
    
    if not day_schedule:
        return f"📭 Выходной! Нет уроков на {day} в классе {class_name}"
    
    # Сортируем уроки по номеру и времени
    sorted_lessons = sorted(day_schedule.items(), 
                          key=lambda x: int(x[0].split('_')[0]))
    
    # Формируем сообщение
    result = f"📅 <b>Расписание на {day.capitalize()}</b>\n"
    result += f"🏫 Класс: <b>{class_name}</b>\n\n"
    
    for lesson_key, lesson_info in sorted_lessons:
        lesson_num, time_range = lesson_key.split('_', 1)
        
        # Форматируем информацию об уроке
        result += f"<b>{lesson_num} урок</b> ⏰ {time_range}\n"
        result += f"   {lesson_info}\n"
        result += "-" * 30 + "\n"
    
    return result

async def format_schedule_for_class_week(class_name: str) -> str:
    """Форматируем расписание на всю неделю"""
    schedule_data = await get_cached_schedule()
    
    if class_name not in schedule_data:
        return f"❌ Класс {class_name} не найден в расписании"
    
    class_data = schedule_data[class_name]
    
    result = f"📅 <b>Расписание на неделю</b>\n"
    result += f"🏫 Класс: <b>{class_name}</b>\n\n"
    
    for day in RUS_WEEKDAYS:
        if day in class_data and class_data[day]:
            day_schedule = class_data[day]
            
            result += f"<b>{day.capitalize()}:</b>\n"
            
            # Сортируем уроки
            sorted_lessons = sorted(day_schedule.items(), 
                                  key=lambda x: int(x[0].split('_')[0]))
            
            for lesson_key, lesson_info in sorted_lessons:
                lesson_num, time_range = lesson_key.split('_', 1)
                result += f"  {lesson_num}) {time_range}: {lesson_info}\n"
            
            result += "\n"
        else:
            result += f"<b>{day.capitalize()}:</b> Выходной\n\n"
    
    return result

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти расписание")],
            [KeyboardButton(text="📋 Список классов")],
            [KeyboardButton(text="🔄 Обновить расписание")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

def get_classes_keyboard(classes: List[str]):
    """Создаем клавиатуру с классами (разбиваем на колонки)"""
    keyboard = []
    row = []
    
    for i, class_name in enumerate(classes):
        row.append(KeyboardButton(text=class_name))
        if len(row) == 3 or i == len(classes) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([KeyboardButton(text="⬅️ Назад")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_days_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Понедельник"), KeyboardButton(text="Вторник")],
            [KeyboardButton(text="Среда"), KeyboardButton(text="Четверг")],
            [KeyboardButton(text="Пятница"), KeyboardButton(text="Суббота")],
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📋 Вся неделя")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

# Обработчики команд
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Команда /start"""
    await message.answer(
        "👋 <b>Привет! Я бот с расписанием школы №25</b>\n\n"
        "Я могу показать расписание уроков для любого класса.\n\n"
        "📌 <b>Как пользоваться:</b>\n"
        "1. Нажми 'Найти расписание'\n"
        "2. Выбери свой класс\n"
        "3. Выбери день недели\n"
        "4. Получи расписание!\n\n"
        "⚠️ <i>Внимание:</i> Расписание обновляется с сайта школы.\n"
        "Если что-то не так - нажми 'Обновить расписание'",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🔍 Найти расписание")
async def find_schedule(message: types.Message, state: FSMContext):
    """Начать поиск расписания"""
    classes = await get_available_classes()
    
    if not classes:
        await message.answer(
            "❌ <b>Список классов пока не загружен</b>\n"
            "Нажмите 'Обновить расписание'",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return
    
    await message.answer(
        "🏫 <b>Выберите ваш класс:</b>",
        parse_mode="HTML",
        reply_markup=get_classes_keyboard(classes)
    )
    await state.set_state(Form.waiting_for_class)

@dp.message(F.text == "📋 Список классов")
async def list_classes(message: types.Message):
    """Показать список доступных классов"""
    classes = await get_available_classes()
    
    if not classes:
        await message.answer("❌ Список классов пока не загружен")
        return
    
    classes_text = "\n".join(sorted(classes))
    await message.answer(
        f"🏫 <b>Доступные классы:</b>\n\n{classes_text}",
        parse_mode="HTML"
    )

@dp.message(F.text == "🔄 Обновить расписание")
async def refresh_schedule(message: types.Message):
    """Обновить кэш расписания"""
    global schedule_cache
    schedule_cache['data'] = None
    
    await message.answer(
        "🔄 <b>Обновляю расписание...</b>",
        parse_mode="HTML"
    )
    
    schedule_data = await fetch_schedule()
    if schedule_data:
        schedule_cache['data'] = schedule_data
        schedule_cache['timestamp'] = datetime.now()
        
        classes_count = len(schedule_data)
        days_count = sum(len(class_data) for class_data in schedule_data.values())
        
        await message.answer(
            f"✅ <b>Расписание обновлено!</b>\n"
            f"Найдено классов: {classes_count}\n"
            f"Дней с расписанием: {days_count}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "❌ <b>Не удалось обновить расписание</b>\n"
            "Проверьте подключение к интернету",
            parse_mode="HTML"
        )

@dp.message(Form.waiting_for_class)
async def process_class(message: types.Message, state: FSMContext):
    """Обработка выбранного класса"""
    class_name = message.text.strip().upper()
    classes = await get_available_classes()
    
    if class_name not in classes:
        await message.answer(
            "❌ Пожалуйста, выберите класс из списка"
        )
        return
    
    await state.update_data(class_name=class_name)
    
    await message.answer(
        f"✅ Выбран класс: <b>{class_name}</b>\n\n"
        f"📅 Выберите день недели:",
        parse_mode="HTML",
        reply_markup=get_days_keyboard()
    )
    await state.set_state(Form.waiting_for_day)

@dp.message(Form.waiting_for_day, F.text.in_(RUS_WEEKDAYS + ["📅 Сегодня", "📋 Вся неделя"]))
async def process_day(message: types.Message, state: FSMContext):
    """Обработка выбранного дня"""
    user_data = await state.get_data()
    class_name = user_data.get('class_name', '')
    
    if not class_name:
        await message.answer("Ошибка: класс не выбран")
        await state.clear()
        return
    
    day = message.text
    
    if day == "📅 Сегодня":
        # Определяем текущий день недели
        today_idx = datetime.now().weekday()
        if today_idx < len(RUS_WEEKDAYS):
            day = RUS_WEEKDAYS[today_idx]
        else:
            day = "понедельник"
        
        day_display = f"сегодня ({day})"
        result = await format_schedule_for_class_day(class_name, day)
        
    elif day == "📋 Вся неделя":
        result = await format_schedule_for_class_week(class_name)
        
    else:
        day_display = day
        result = await format_schedule_for_class_day(class_name, day)
    
    # Если результат слишком длинный, разбиваем на части
    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for i, part in enumerate(parts):
            await message.answer(
                part,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
    else:
        await message.answer(
            result,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

@dp.message(F.text == "⬅️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    """Возврат назад"""
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
    
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ-панель"""
    if message.from_user.id != 123456789:  # Замени на свой ID
        return
    
    schedule_data = await get_cached_schedule()
    
    stats = f"📊 <b>Статистика бота:</b>\n\n"
    stats += f"🏫 Классов в базе: {len(schedule_data)}\n"
    
    if schedule_data:
        # Подсчет дней с расписанием
        days_with_schedule = 0
        for class_data in schedule_data.values():
            days_with_schedule += len(class_data)
        
        stats += f"📅 Дней с расписанием: {days_with_schedule}\n"
        
        # Примеры классов
        sample_classes = list(schedule_data.keys())[:5]
        stats += f"\n<b>Примеры классов:</b>\n" + "\n".join(sample_classes)
    
    stats += f"\n\n⏰ Кэш обновлен: {schedule_cache['timestamp']}"
    
    await message.answer(stats, parse_mode="HTML")

# Запуск бота
async def main():
    logger.info("=" * 50)
    logger.info("🏫 ЗАПУСК БОТА РАСПИСАНИЯ ШКОЛЫ №25")
    logger.info("=" * 50)
    
    # Предзагрузка расписания
    await get_cached_schedule()
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())