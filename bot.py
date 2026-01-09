import telebot
import os
import sys
import logging
import time

# Настройка логирования для Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Добавляем путь для локальных модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Пытаемся импортировать наши модули
try:
    import download_schedule
    import schedule_parser
    LOCAL_MODULES = True
    logger.info("✅ Локальные модули загружены")
except ImportError as e:
    logger.error(f"⚠️  Не удалось импортировать локальные модули: {e}")
    LOCAL_MODULES = False

# Получаем токен из переменных окружения Railway
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    logger.error("❌ Токен не найден! Установите переменную TELEGRAM_BOT_TOKEN в Railway")
    sys.exit(1)

logger.info(f"✅ Токен получен: {TOKEN[:10]}...")

# Создаем бота
bot = telebot.TeleBot(TOKEN)

# ====== ОСНОВНЫЕ ФУНКЦИИ ======

def update_schedule_file():
    """Обновляет файл расписания"""
    if not LOCAL_MODULES:
        return False, "Модули расписания не загружены"
    
    try:
        logger.info("🔄 Начинаю обновление расписания...")
        download_schedule.download_schedule_from_site()
        
        import importlib
        importlib.reload(schedule_parser)
        
        if os.path.exists('school_schedule.csv'):
            file_size = os.path.getsize('school_schedule.csv')
            return True, f"Расписание обновлено! Размер файла: {file_size} байт"
        else:
            return False, "Файл расписания не был создан"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

# ====== ОБРАБОТЧИКИ КОМАНД ======

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработчик команд /start и /help"""
    help_text = (
        "👋 *Школьный бот расписания*\n\n"
        "📋 *Команды:*\n"
        "/start, /help - эта справка\n"
        "/schedule - получить расписание\n"
        "/update - обновить с сайта\n"
        "/classes - список классов\n\n"
        "💡 *Или просто отправьте номер класса:*\n"
        "Например: 5А, 10Е, 8 Б"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['update'])
def update_command(message):
    """Обновление расписания"""
    bot.reply_to(message, "🔄 Обновляю расписание...", parse_mode='Markdown')
    success, msg = update_schedule_file()
    
    if success:
        bot.reply_to(message, f"✅ {msg}", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {msg}", parse_mode='Markdown')

@bot.message_handler(commands=['schedule'])
def schedule_command(message):
    """Запрос расписания"""
    bot.reply_to(message, 
        "📋 *Отправьте номер класса:*\n\n"
        "Например: 5А, 10Е, 8 Б\n\n"
        "Или /classes для списка классов",
        parse_mode='Markdown')

@bot.message_handler(commands=['classes'])
def classes_command(message):
    """Список классов"""
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули не загружены")
        return
    
    try:
        classes = schedule_parser.get_available_classes()
        if classes:
            text = f"📋 *Доступные классы ({len(classes)}):*\n\n" + "\n".join(f"• {c}" for c in classes[:15])
            if len(classes) > 15:
                text += f"\n\n... и еще {len(classes)-15}"
            bot.reply_to(message, text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Классы не найдены. Используйте /update", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработка текста (номеров классов)"""
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    if not any(char.isdigit() for char in text):
        bot.reply_to(message, "Введите номер класса (например: 5А) или команду /help")
        return
    
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули не загружены")
        return
    
    try:
        lessons = schedule_parser.get_schedule_for_class(text)
        
        if not lessons:
            bot.reply_to(message, f"❌ Класс '{text}' не найден", parse_mode='Markdown')
            return
        
        response = f"📚 *Расписание для {text}:*\n\n"
        for i, lesson in enumerate(lessons, 1):
            response += f"*{i}. {lesson['time']}*\n"
            if lesson['data']:
                response += f"   {lesson['data'][0]}\n"
            response += "\n"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}", parse_mode='Markdown')

# ====== ЗАПУСК БОТА ======

def main():
    """Основная функция"""
    logger.info("=" * 60)
    logger.info("🤖 ШКОЛЬНЫЙ БОТ ЗАПУСКАЕТСЯ НА RAILWAY")
    logger.info("=" * 60)
    
    # Проверяем файл расписания
    if LOCAL_MODULES:
        if os.path.exists('school_schedule.csv'):
            logger.info("✅ Файл расписания найден")
        else:
            logger.info("📭 Файл расписания не найден")
            logger.info("ℹ️  Используйте /update в боте для загрузки")
    
    # Запускаем бота с перезапуском при ошибках
    while True:
        try:
            logger.info("🔄 Запуск polling...")
            bot.polling(none_stop=True, interval=2, timeout=30)
        except Exception as e:
            logger.error(f"❌ Ошибка polling: {e}")
            logger.info("⏳ Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == '__main__':
    main()