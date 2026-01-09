import re

def read_schedule_file():
    """Читает файл расписания (как в исходном коде)"""
    try:
        with open('school_schedule.csv', 'r', encoding='utf-8') as f:
            return f.readlines()
    except FileNotFoundError:
        # Если файла нет - возвращаем пустой список (Railway при первом запуске)
        return []

# Глобальная переменная как в исходном коде
lines = read_schedule_file()

def normalize_class_name(class_name):
    """Нормализует название класса: удаляет пробелы, приводит к верхнему регистру"""
    # Удаляем все пробелы
    normalized = class_name.replace(" ", "")
    # Приводим к верхнему регистру
    normalized = normalized.upper()
    return normalized

def find_class_position(class_name):
    """Находит позицию класса в файле (точная копия из import csv.py)"""
    normalized_target = normalize_class_name(class_name)
    
    for line_num, line in enumerate(lines):
        cells = line.strip().split(',')
        for i, cell in enumerate(cells):
            # Нормализуем каждую ячейку
            cell_normalized = normalize_class_name(cell)
            if normalized_target == cell_normalized:
                return i, line_num
    return -1, -1

def get_schedule_for_class(class_name):
    """Универсальное расписание - работает с любым форматом ввода (как в исходном коде)"""
    
    # Находим позицию класса
    class_position, start_line = find_class_position(class_name)
    
    if class_position == -1:
        return None
    
    # Собираем уроки
    lessons = []
    
    for line_num in range(start_line + 1, len(lines)):
        line = lines[line_num].strip()
        cells = line.split(',')
        
        # Останавливаемся при новой секции
        if len(cells) > 1 and 'ВРЕМЯ' in cells[1]:
            break
        
        # Ищем строки с временем (точное условие из исходного кода)
        if len(cells) > 1 and ('–' in cells[1] or '-' in cells[1]):
            time_str = cells[1].strip()
            
            # Собираем данные из трех строк вокруг времени (как в исходном коде)
            data_parts = []
            for offset in range(-1, 2):  # -1, 0, 1 (точное соответствие)
                check_line_num = line_num + offset
                if 0 <= check_line_num < len(lines):
                    check_line = lines[check_line_num].strip()
                    if check_line:
                        check_cells = check_line.split(',')
                        if len(check_cells) > class_position:
                            data = check_cells[class_position].strip()
                            if data:
                                data_parts.append(data)
            
            # Добавляем урок если есть данные
            if data_parts:
                lessons.append({
                    'time': time_str,
                    'data': data_parts
                })
    
    return lessons

def format_schedule_message(class_name, lessons):
    """Форматирует расписание в читаемое сообщение (как в исходном коде)"""
    if not lessons:
        return f"📭 Нет уроков для класса {class_name}"
    
    message = f"📚 *Расписание для класса {class_name}:*\n\n"
    
    for i, lesson in enumerate(lessons, 1):
        message += f"*{i}. {lesson['time']}*\n"
        if len(lesson['data']) >= 1:
            message += f"   📖 {lesson['data'][0]}\n"
        if len(lesson['data']) >= 2:
            message += f"   👨‍🏫 {lesson['data'][1]}\n"
        if len(lesson['data']) >= 3:
            message += f"   🏫 {lesson['data'][2]}\n"
        message += "\n"
    
    return message

def get_available_classes():
    """Получает список доступных классов из файла (аналогично исходному)"""
    classes = set()
    
    for line in lines:
        cells = line.strip().split(',')
        for cell in cells:
            # Ищем ячейки с названиями классов (формат "5 А", "10Е" и т.д.)
            cell_clean = cell.strip()
            if re.match(r'^\d+\s*[А-ЯA-Z]$', cell_clean, re.IGNORECASE):
                classes.add(cell_clean)
    
    # Сортируем как в исходном коде: сначала по цифре, потом по букве
    return sorted(list(classes), key=lambda x: (int(re.search(r'\d+', x).group()), x))

# Дополнительные функции для Railway (чтобы не падало при отсутствии файла)

def reload_schedule():
    """Перезагружает расписание из файла (для Railway)"""
    global lines
    lines = read_schedule_file()
    return lines

def has_schedule_file():
    """Проверяет наличие файла расписания"""
    try:
        with open('school_schedule.csv', 'r', encoding='utf-8'):
            return True
    except FileNotFoundError:
        return False