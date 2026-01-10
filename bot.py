import telebot
import os
import sys
import logging
import time
import re

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
        "📋 *Основные команды:*\n"
        "/start, /help - эта справка\n"
        "/schedule - получить расписание класса\n"
        "/update - обновить с сайта\n"
        "/classes - список классов\n\n"
        "👨‍🏫 *Команды для учителей:*\n"
        "/teacher <фамилия> - расписание учителя\n"
        "/teachers <часть> - поиск учителя\n\n"
        "💡 *Или просто отправьте:*\n"
        "• Номер класса: 5А, 10Е\n"
        "• Фамилию учителя: Протасова\n"
        "• Часть фамилии: про (для поиска)"
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

@bot.message_handler(commands=['teacher'])
def teacher_command(message):
    """Поиск расписания по учителю"""
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули не загружены")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message,
                     "👨‍🏫 *Поиск расписания учителя:*\n\n"
                     "✏️ *Использование:* /teacher <фамилия>\n"
                     "Например: /teacher Протасова\n\n"
                     "🔍 Для поиска по части фамилии:\n"
                     "/teachers <часть фамилии>\n"
                     "Например: /teachers про",
                     parse_mode='Markdown')
        return
    
    teacher_name = ' '.join(args[1:])
    
    try:
        teacher_info = schedule_parser.get_schedule_by_teacher(teacher_name)
        response_text = schedule_parser.format_teacher_schedule(teacher_info)
        bot.reply_to(message, response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка поиска учителя {teacher_name}: {e}")
        bot.reply_to(message, 
                     f"❌ Ошибка при поиске учителя: {str(e)}\n"
                     "💡 Попробуйте:\n"
                     "• Проверить написание фамилии\n"
                     "• Использовать /teachers для поиска\n"
                     "• Обновить расписание /update",
                     parse_mode='Markdown')

@bot.message_handler(commands=['teachers'])
def search_teachers_command(message):
    """Поиск учителей по части фамилии"""
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули не загружены")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message,
                     "🔍 *Поиск учителей:*\n\n"
                     "✏️ *Использование:* /teachers <часть_фамилии>\n"
                     "Например: /teachers Про\n"
                     "Найдет: Протасова, Прокопьев и т.д.\n\n"
                     "💡 Для полного расписания:\n"
                     "/teacher <полная фамилия>",
                     parse_mode='Markdown')
        return
    
    search_query = args[1]
    
    try:
        matches = schedule_parser.search_teachers_by_substring(search_query)
        response_text = schedule_parser.format_teachers_search_results(matches, search_query)
        bot.reply_to(message, response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка поиска учителей {search_query}: {e}")
        bot.reply_to(message, f"❌ Ошибка: {str(e)}", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработка текстовых сообщений (классы и учителя)"""
    user_input = message.text.strip()
    
    if user_input.startswith('/'):
        return
    
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули не загружены")
        return
    
    if not schedule_parser.has_schedule_file():
        bot.reply_to(message,
            "❌ *Файл расписания не найден!*\n\n"
            "📥 Используйте команду /update чтобы скачать актуальное расписание.",
            parse_mode='Markdown')
        return
    
    try:
        # Пробуем распознать как класс (сначала проверяем формат класса)
        if re.match(r'^\d+\s*[А-Яа-яA-Za-z]$', user_input, re.IGNORECASE):
            # Это похоже на класс - ищем расписание класса
            lessons = schedule_parser.get_schedule_for_class(user_input)
            
            if lessons is None:
                # Если класс не найден, пробуем поискать как учителя
                teacher_info = schedule_parser.get_schedule_by_teacher(user_input)
                if teacher_info:
                    # Нашли учителя
                    response_text = schedule_parser.format_teacher_schedule(teacher_info)
                    bot.reply_to(message, response_text, parse_mode='Markdown')
                    return
                else:
                    # Не нашли ни класс, ни учителя
                    bot.reply_to(message,
                        f"❌ *{user_input}* не найден.\n\n"
                        "💡 *Попробуйте:*\n"
                        "• Другой формат (5А, 5 А, 5а)\n"
                        "• Полную фамилию учителя\n"
                        "• Команду /classes для списка классов\n"
                        "• Команду /teachers для поиска учителя\n"
                        "• Команду /update чтобы обновить расписание",
                        parse_mode='Markdown')
                    return
            
            # Если нашли класс - выводим расписание
            message_text = schedule_parser.format_schedule_for_telegram(user_input, lessons)
            bot.reply_to(message, message_text, parse_mode='Markdown')
            
        else:
            # Не похоже на класс - ищем как учителя
            teacher_info = schedule_parser.get_schedule_by_teacher(user_input)
            
            if teacher_info:
                # Нашли учителя
                response_text = schedule_parser.format_teacher_schedule(teacher_info)
                bot.reply_to(message, response_text, parse_mode='Markdown')
            else:
                # Не нашли ни класс, ни учителя - предлагаем помощь
                bot.reply_to(message,
                    f"❌ *{user_input}* не найден.\n\n"
                    "💡 *Что можно сделать:*\n"
                    "• Ввести номер класса (5А, 10Б)\n"
                    "• Ввести фамилию учителя\n"
                    "• Использовать /teachers для поиска\n"
                    "• Использовать /classes для списка классов",
                    parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса '{user_input}': {e}")
        bot.reply_to(message,
            f"❌ *Ошибка при обработке запроса:* {str(e)}\n"
            "Попробуйте обновить расписание командой /update",
            parse_mode='Markdown')

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
            
            # Инициализируем кэш учителей при запуске
            try:
                teacher_index = schedule_parser.get_cached_teacher_index()
                logger.info(f"✅ Индекс учителей создан: {len(teacher_index)} учителей")
            except Exception as e:
                logger.error(f"⚠️ Ошибка создания индекса учителей: {e}")
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