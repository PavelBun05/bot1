import re
import os

def read_schedule_file():
    """Читает файл расписания"""
    try:
        if not os.path.exists('school_schedule.csv'):
            return []  # Возвращаем пустой список если файла нет
        with open('school_schedule.csv', 'r', encoding='utf-8') as f:
            return f.readlines()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return []

lines = read_schedule_file()

def reload_schedule():
    """Перезагружает расписание из файла"""
    global lines
    lines = read_schedule_file()
    return lines

def normalize_class_name(class_name):
    """Нормализует название класса"""
    return class_name.replace(" ", "").upper()

def find_class_position(class_name):
    """Находит позицию класса"""
    target = normalize_class_name(class_name)
    
    for line_num, line in enumerate(lines):
        cells = line.strip().split(',')
        for i, cell in enumerate(cells):
            if normalize_class_name(cell) == target:
                return i, line_num
    return -1, -1

def get_schedule_for_class(class_name):
    """Получает расписание для класса"""
    if not lines:  # Если файл еще не скачан
        return None
    
    col, start_line = find_class_position(class_name)
    if col == -1:
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
                        if len(check_cells) > col:
                            data = check_cells[col].strip()
                            if data:
                                data_parts.append(data)
            
            if data_parts:
                lessons.append({
                    'time': time_str,
                    'data': data_parts
                })
    
    return lessons

def get_available_classes():
    """Получает список классов"""
    if not lines:  # Если файл еще не скачан
        return []
    
    classes = set()
    
    for line in lines:
        cells = line.strip().split(',')
        for cell in cells:
            cell = cell.strip()
            if re.match(r'^\d+\s*[А-ЯA-Z]$', cell, re.IGNORECASE):
                classes.add(cell)
    
    return sorted(list(classes))
