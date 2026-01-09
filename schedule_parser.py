import re

def read_schedule_file():
    """Читает файл расписания"""
    try:
        with open('school_schedule.csv', 'r', encoding='utf-8') as f:
            return f.readlines()
    except FileNotFoundError:
        return []

lines = read_schedule_file()

def normalize_class_name(class_name):
    """Нормализует название класса"""
    normalized = class_name.replace(" ", "")
    normalized = normalized.upper()
    return normalized

def find_class_position(class_name):
    """Находит позицию класса в файле"""
    normalized_target = normalize_class_name(class_name)
    
    for line_num, line in enumerate(lines):
        cells = line.strip().split(',')
        for i, cell in enumerate(cells):
            cell_normalized = normalize_class_name(cell)
            if normalized_target == cell_normalized:
                return i, line_num
    return -1, -1

def get_schedule_for_class(class_name):
    """Получает расписание для класса"""
    class_position, start_line = find_class_position(class_name)
    
    if class_position == -1:
        return None
    
    lessons = []
    
    for line_num in range(start_line + 1, len(lines)):
        line = lines[line_num].strip()
        cells = line.split(',')
        
        if len(cells) > 1 and 'ВРЕМЯ' in cells[1]:
            break
        
        if len(cells) > 1 and ('–' in cells[1] or '-' in cells[1]):
            time_str = cells[1].strip()
            
            data_parts = []
            for offset in range(-1, 2):
                check_line_num = line_num + offset
                if 0 <= check_line_num < len(lines):
                    check_line = lines[check_line_num].strip()
                    if check_line:
                        check_cells = check_line.split(',')
                        if len(check_cells) > class_position:
                            data = check_cells[class_position].strip()
                            if data:
                                data_parts.append(data)
            
            if data_parts:
                lessons.append({
                    'time': time_str,
                    'data': data_parts
                })
    
    return lessons

def format_schedule_for_telegram(class_name, lessons):
    """Форматирует расписание для Telegram (как в консоли)"""
    if not lessons:
        return f"📭 Нет уроков для класса {class_name}"
    
    message = f"📚 *Расписание для класса {class_name}:*\n\n"
    
    for i, lesson in enumerate(lessons, 1):
        message += f"*{i}. {lesson['time']}*\n"
        
        # Первая строка: предмет (если есть)
        if len(lesson['data']) >= 1 and lesson['data'][0]:
            message += f"   📖 {lesson['data'][0]}\n"
        
        # Вторая строка: учитель (если есть)
        if len(lesson['data']) >= 2 and lesson['data'][1]:
            message += f"   👨‍🏫 {lesson['data'][1]}\n"
        
        # Третья строка: кабинет (если есть)
        if len(lesson['data']) >= 3 and lesson['data'][2]:
            message += f"   🏫 {lesson['data'][2]}\n"
        
        message += "\n"
    
    return message

def format_schedule_for_console(class_name, lessons):
    """Форматирует расписание для консоли (старый формат)"""
    if not lessons:
        return f"📭 Нет уроков для класса {class_name}"
    
    message = f"\n{'='*60}\nРАСПИСАНИЕ ДЛЯ КЛАССА '{class_name}':\n{'='*60}\n"
    
    if lessons:
        message += f"\n📚 Найдено уроков: {len(lessons)}\n\n"
        for i, lesson in enumerate(lessons, 1):
            message += f"{i}. {lesson['time']}\n"
            if len(lesson['data']) >= 1 and lesson['data'][0]:
                message += f"   📖 {lesson['data'][0]}\n"
            if len(lesson['data']) >= 2 and lesson['data'][1]:
                message += f"   👨‍🏫 {lesson['data'][1]}\n"
            if len(lesson['data']) >= 3 and lesson['data'][2]:
                message += f"   🏫 {lesson['data'][2]}\n"
            message += "\n"
    else:
        message += "\n📭 Нет уроков на сегодня"
    
    return message

def get_available_classes():
    """Получает список доступных классов"""
    classes = set()
    
    for line in lines:
        cells = line.strip().split(',')
        for cell in cells:
            cell_clean = cell.strip()
            if re.match(r'^\d+\s*[А-ЯA-Z]$', cell_clean, re.IGNORECASE):
                classes.add(cell_clean)
    
    return sorted(list(classes), key=lambda x: (int(re.search(r'\d+', x).group()), x))

def reload_schedule():
    """Перезагружает расписание из файла"""
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