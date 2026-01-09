import telebot
import os
import sys
import logging
import time

# Настройка логирования
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
    print("✅ Локальные модули загружены")
except ImportError as e:
    print(f"⚠️  Не удалось импортировать локальные модули: {e}")
    print("Убедитесь, что в папке есть файлы:")
    print("  - download_schedule.py")
    print("  - schedule_parser.py")
    LOCAL_MODULES = False

# ====== ВАШ ТОКЕН БОТА ======
# ЗАМЕНИТЕ ЭТУ СТРОКУ НА ВАШ РЕАЛЬНЫЙ ТОКЕН!
TOKEN = "8318435259:AAGWFqs9k715u1SwXgUx3PiZ_MKDxkVz9mk"
# ============================

# Проверяем токен
if not TOKEN or ":" not in TOKEN:
    print("❌ ОШИБКА: Не установлен токен бота!")
    print("Получите токен у @BotFather в Telegram")
    print("И замените строку TOKEN в коде на ваш токен")
    sys.exit(1)

print(f"✅ Используется токен: {TOKEN[:10]}...")

# Создаем бота
try:
    bot = telebot.TeleBot(TOKEN)
    print("✅ Бот создан")
except Exception as e:
    print(f"❌ Ошибка при создании бота: {e}")
    sys.exit(1)

# ====== ФУНКЦИЯ ОБНОВЛЕНИЯ РАСПИСАНИЯ ======

def update_schedule_file():
    """Обновляет файл расписания"""
    if not LOCAL_MODULES:
        return False, "Модули расписания не загружены"
    
    try:
        print("🔄 Начинаю обновление расписания...")
        
        # Скачиваем расписание
        download_schedule.download_schedule_from_site()
        
        # Перезагружаем модуль schedule_parser для чтения нового файла
        import importlib
        importlib.reload(schedule_parser)
        
        # Проверяем, что файл создан
        if os.path.exists('school_schedule.csv'):
            file_size = os.path.getsize('school_schedule.csv')
            print(f"✅ Расписание обновлено. Размер файла: {file_size} байт")
            return True, "Расписание успешно обновлено!"
        else:
            return False, "Файл расписания не был создан"
            
    except Exception as e:
        error_msg = f"Ошибка при обновлении: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg

# ====== ОБРАБОТЧИКИ КОМАНД ======

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start"""
    user = message.from_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"🤖 Я бот для просмотра школьного расписания.\n\n"
        f"📋 *Доступные команды:*\n"
        f"/start - начать работу\n"
        f"/help - помощь\n"
        f"/schedule - получить расписание\n"
        f"/update - ОБНОВИТЬ расписание с сайта\n"
        f"/classes - список классов\n\n"
        f"💡 *Просто отправьте номер класса:*\n"
        f"Например: 5А, 10Е, 8 Б"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    """Обработчик команды /help"""
    help_text = (
        "📚 *Помощь по использованию бота:*\n\n"
        "*/schedule* - получить расписание для класса\n"
        "*/update* - ОБНОВИТЬ расписание с сайта (скачать актуальное)\n"
        "*/classes* - показать список доступных классов\n\n"
        "💡 *Как получить расписание:*\n"
        "1. Отправьте номер класса (например: 5А)\n"
        "2. Или используйте команду /schedule\n\n"
        "🔄 *Обновление расписания:*\n"
        "Используйте /update чтобы скачать актуальное расписание с сайта школы\n\n"
        "📝 *Форматы классов:*\n"
        "'5А', '10Е', '8 Б', '5 А' и т.д."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['update'])
def update_command(message):
    """Обработчик команды /update - ОБНОВЛЯЕТ расписание"""
    bot.reply_to(message, "🔄 *Начинаю обновление расписания...*\nПожалуйста, подождите ⏳", 
                 parse_mode='Markdown')
    
    success, result_msg = update_schedule_file()
    
    if success:
        # Показываем информацию о файле
        try:
            if os.path.exists('school_schedule.csv'):
                file_size = os.path.getsize('school_schedule.csv')
                file_info = f"\n📁 Размер файла: {file_size} байт"
                
                # Показываем сколько классов найдено
                classes = schedule_parser.get_available_classes()
                if classes:
                    file_info += f"\n📋 Найдено классов: {len(classes)}"
                    file_info += f"\nПримеры: {', '.join(classes[:5])}"
                    if len(classes) > 5:
                        file_info += f" и ещё {len(classes)-5}..."
                else:
                    file_info += "\n⚠️ Классы не найдены в файле"
                
                result_msg += file_info
        except:
            pass
        
        bot.reply_to(message, f"✅ *{result_msg}*", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ *{result_msg}*", parse_mode='Markdown')

@bot.message_handler(commands=['schedule'])
def ask_for_class(message):
    """Обработчик команды /schedule"""
    bot.reply_to(message, 
        "📋 *Отправьте номер класса:*\n\n"
        "Например: 5А, 10Е, 8 Б\n\n"
        "Или используйте /classes чтобы увидеть список доступных классов.",
        parse_mode='Markdown')

@bot.message_handler(commands=['classes'])
def show_classes_command(message):
    """Обработчик команды /classes"""
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули расписания не загружены.")
        return
    
    try:
        # Проверяем наличие файла
        if not os.path.exists('school_schedule.csv'):
            bot.reply_to(message, 
                "❌ *Файл расписания не найден!*\n"
                "Используйте команду /update чтобы скачать расписание",
                parse_mode='Markdown')
            return
        
        classes = schedule_parser.get_available_classes()
        
        if not classes:
            bot.reply_to(message, 
                "❌ *Классы не найдены в файле!*\n"
                "Возможно файл поврежден. Используйте /update",
                parse_mode='Markdown')
            return
        
        if len(classes) <= 15:
            classes_text = "📋 *Доступные классы:*\n\n" + "\n".join(f"• {c}" for c in classes)
        else:
            classes_text = f"📋 *Доступные классы ({len(classes)}):*\n\n" + "\n".join(f"• {c}" for c in classes[:15])
            classes_text += f"\n\n... и еще {len(classes) - 15} классов"
        
        classes_text += "\n\n💡 Просто отправьте номер класса"
        
        bot.reply_to(message, classes_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при получении классов: {e}")
        bot.reply_to(message, 
            f"❌ *Ошибка при чтении файла:* {str(e)}\n"
            "Попробуйте обновить расписание командой /update",
            parse_mode='Markdown')

# ====== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ======

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    """Обработчик текстовых сообщений"""
    user_input = message.text.strip()
    
    # Пропускаем команды
    if user_input.startswith('/'):
        return
    
    # Проверяем, похоже ли на номер класса
    if not any(char.isdigit() for char in user_input):
        bot.reply_to(message, 
            "🤖 Я понимаю номера классов (например: 5А, 10Е) или команды.\n"
            "Используйте /help для списка команд.")
        return
    
    if not LOCAL_MODULES:
        bot.reply_to(message, "❌ Модули расписания не загружены.")
        return
    
    # Проверяем наличие файла расписания
    if not os.path.exists('school_schedule.csv'):
        bot.reply_to(message,
            "❌ *Файл расписания не найден!*\n\n"
            "📥 Используйте команду /update чтобы скачать актуальное расписание",
            parse_mode='Markdown')
        return
    
    try:
        # Получаем расписание
        lessons = schedule_parser.get_schedule_for_class(user_input)
        
        if lessons is None:
            bot.reply_to(message, 
                f"❌ Класс *{user_input}* не найден.\n\n"
                "💡 *Попробуйте:*\n"
                "• Другой формат (5А, 5 А, 5а)\n"
                "• Команду /classes для списка\n"
                "• Команду /update чтобы обновить расписание",
                parse_mode='Markdown')
            return
        
        # Форматируем расписание
        if not lessons:
            bot.reply_to(message, f"📭 Нет уроков для класса *{user_input}*", parse_mode='Markdown')
            return
        
        schedule_text = f"📚 *Расписание для {user_input}:*\n\n"
        
        for i, lesson in enumerate(lessons, 1):
            schedule_text += f"*{i}. {lesson['time']}*\n"
            if len(lesson['data']) >= 1 and lesson['data'][0]:
                schedule_text += f"   📖 {lesson['data'][0]}\n"
            if len(lesson['data']) >= 2 and lesson['data'][1]:
                schedule_text += f"   👨‍🏫 {lesson['data'][1]}\n"
            if len(lesson['data']) >= 3 and lesson['data'][2]:
                schedule_text += f"   🏫 {lesson['data'][2]}\n"
            schedule_text += "\n"
        
        # Добавляем информацию о файле
        try:
            file_time = time.ctime(os.path.getmtime('school_schedule.csv'))
            schedule_text += f"\n_📅 Файл обновлен: {file_time}_"
        except:
            pass
        
        bot.reply_to(message, schedule_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка при обработке класса {user_input}: {e}")
        bot.reply_to(message, 
            f"❌ *Ошибка при получении расписания:* {str(e)}\n"
            "Попробуйте обновить расписание командой /update",
            parse_mode='Markdown')

# ====== ЗАПУСК БОТА ======

def main():
    """Основная функция запуска бота"""
    print("=" * 60)
    print("🤖 ШКОЛЬНЫЙ БОТ РАСПИСАНИЯ")
    print("=" * 60)
    
    # Проверяем наличие файла расписания
    if LOCAL_MODULES:
        if os.path.exists('school_schedule.csv'):
            file_time = time.ctime(os.path.getmtime('school_schedule.csv'))
            file_size = os.path.getsize('school_schedule.csv')
            print(f"✅ Файл расписания найден")
            print(f"   📅 Последнее изменение: {file_time}")
            print(f"   📁 Размер: {file_size} байт")
        else:
            print("📭 Файл расписания не найден")
            print("ℹ️  Используйте команду /update в боте для скачивания")
    else:
        print("⚠️  Локальные модули не загружены")
    
    print(f"\n✅ Токен бота: {'Установлен' if ':' in TOKEN else 'НЕ установлен!'}")
    
    if ':' not in TOKEN:
        print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Токен не установлен!")
        print("1. Получите токен у @BotFather в Telegram")
        print("2. Замените строку TOKEN в коде на ваш токен")
        print("3. Перезапустите бота")
        return
    
    print("\n" + "=" * 60)
    print("🚀 Бот запускается...")
    print("=" * 60 + "\n")
    
    # Функция перезапуска при ошибках
    while True:
        try:
            print(f"🕒 {time.strftime('%H:%M:%S')} - Запуск polling...")
            bot.polling(none_stop=True, interval=2, timeout=30)
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            print("⏳ Перезапуск через 5 секунд...")
            time.sleep(5)

if __name__ == '__main__':
    main()