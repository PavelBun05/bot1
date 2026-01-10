import re
import time
from collections import defaultdict

def read_schedule_file():
    """Читает файл расписания"""
    try:
        with open('school_schedule.csv', 'r', encoding='utf-8') as f:
            return f.readlines()
    except FileNotFoundError:
        return []

lines = read_schedule_file()

# Кэши для производительности
_teacher_index_cache = None
_teacher_index_cache_time = None
CACHE_TIMEOUT = 300  # 5 минут

def normalize_class_name(class_name):
    """Нормализует название класса"""
    normalized = class_name.replace(" ", "")
    normalized = normalized.upper()
    return normalized

def find_all_rows_with_classes():
    """
    Находит ВСЕ строки, содержащие номера классов.
    Возвращает список кортежей (номер_строки, список_классов_в_строке)
    """
    class_rows = []
    
    for line_num, line in enumerate(lines):
        cells = line.strip().split(',')
        
        # Собираем все классы из строки
        classes_in_row = []
        for cell in cells:
            cell_clean = cell.strip()
            if re.match(r'^\d+\s*[А-ЯA-Z]$', cell_clean, re.IGNORECASE):
                classes_in_row.append(cell_clean)
        
        # Если найдено достаточно классов, добавляем в список
        if len(classes_in_row) >= 3:  # Минимум 3 класса для уверенности
            class_rows.append((line_num, classes_in_row))
    
    return class_rows

def get_lessons_for_class_at_position(class_name, class_position, class_row_line):
    """
    Получает все уроки для класса в конкретной позиции и строке.
    """
    lessons = []
    
    # Ищем строки с временем уроков ниже строки с классом
    for line_num in range(class_row_line + 1, len(lines)):
        line = lines[line_num].strip()
        if not line:
            continue
        
        cells = line.split(',')
        
        # Если это строка со временем урока
        if len(cells) > 1 and ('–' in cells[1] or '-' in cells[1]):
            time_str = cells[1].strip()
            
            # Собираем данные урока (учитель, предмет, кабинет)
            data_parts = []
            
            # Проверяем текущую строку и соседние
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
            
            # Формируем информацию об уроке
            if data_parts:
                lesson_info = {
                    'time': time_str,
                    'subject': data_parts[0] if len(data_parts) > 0 else '',
                    'teacher': data_parts[1] if len(data_parts) > 1 else '',
                    'classroom': data_parts[2] if len(data_parts) > 2 else '',
                    'raw_data': data_parts
                }
                lessons.append(lesson_info)
        
        # Если встречаем новую строку с классами или "ВРЕМЯ" - прерываем
        if len(cells) > 1 and 'ВРЕМЯ' in cells[1]:
            break
        # Проверяем, не новая ли это строка с классами
        if has_classes_in_line(line):
            break
    
    return lessons

def has_classes_in_line(line):
    """Проверяет, содержит ли строка номера классов."""
    cells = line.strip().split(',')
    class_count = 0
    for cell in cells:
        cell_clean = cell.strip()
        if re.match(r'^\d+\s*[А-ЯA-Z]$', cell_clean, re.IGNORECASE):
            class_count += 1
    
    return class_count >= 3

def get_day_section_for_line(line_num):
    """Определяет день недели для строки."""
    # Ищем ближайший заголовок с днем недели выше
    for i in range(line_num, -1, -1):
        if i < len(lines):
            cells = lines[i].strip().split(',')
            for cell in cells:
                cell_upper = cell.upper()
                if 'ПОНЕДЕЛЬНИК' in cell_upper:
                    return 'ПОНЕДЕЛЬНИК'
                elif 'ВТОРНИК' in cell_upper:
                    return 'ВТОРНИК'
                elif 'СРЕДА' in cell_upper:
                    return 'СРЕДА'
                elif 'ЧЕТВЕРГ' in cell_upper:
                    return 'ЧЕТВЕРГ'
                elif 'ПЯТНИЦА' in cell_upper:
                    return 'ПЯТНИЦА'
                elif 'СУББОТА' in cell_upper:
                    return 'СУББОТА'
    
    return 'Расписание'

def create_teacher_schedule_index():
    """
    Создает индекс расписания по учителям.
    Возвращает словарь: {учитель: [список_уроков]}
    """
    teacher_index = defaultdict(list)
    
    # Находим все строки с классами
    class_rows = find_all_rows_with_classes()
    
    for line_num, classes_in_row in class_rows:
        # Получаем все классы и их позиции в этой строке
        cells = lines[line_num].strip().split(',')
        
        # Для каждого класса в строке
        for col_num, cell in enumerate(cells):
            cell_clean = cell.strip()
            if not re.match(r'^\d+\s*[А-ЯA-Z]$', cell_clean, re.IGNORECASE):
                continue
            
            class_name = cell_clean
            class_position = col_num
            
            # Ищем уроки для этого класса
            lessons = get_lessons_for_class_at_position(class_name, class_position, line_num)
            
            # Добавляем уроки в индекс по учителям
            for lesson in lessons:
                if 'teacher' in lesson and lesson['teacher']:
                    teacher_names_raw = lesson['teacher'].strip()
                    
                    # Обрабатываем несколько учителей через слэш
                    if '/' in teacher_names_raw or '\\' in teacher_names_raw or '\/' in teacher_names_raw:
                        # Заменяем разные виды слэшей на стандартный
                        teacher_names_clean = re.sub(r'[\\\/]+', '/', teacher_names_raw)
                        # Разделяем учителей
                        individual_teachers = [t.strip() for t in teacher_names_clean.split('/') if t.strip()]
                    else:
                        individual_teachers = [teacher_names_raw]
                    
                    # Добавляем урок для каждого учителя
                    for teacher_name in individual_teachers:
                        if not teacher_name:
                            continue
                            
                        lesson_info = {
                            'time': lesson['time'],
                            'subject': lesson.get('subject', ''),
                            'classroom': lesson.get('classroom', ''),
                            'class_name': class_name,
                            'day_section': get_day_section_for_line(line_num),
                            'raw_data': lesson.get('raw_data', []),
                            'original_teacher_field': teacher_names_raw  # Сохраняем оригинальное поле
                        }
                        
                        teacher_index[teacher_name].append(lesson_info)
    
    return dict(teacher_index)



def get_cached_teacher_index():
    """Получает закешированный индекс учителей."""
    global _teacher_index_cache, _teacher_index_cache_time
    
    current_time = time.time()
    
    if (_teacher_index_cache is None or 
        _teacher_index_cache_time is None or 
        current_time - _teacher_index_cache_time > CACHE_TIMEOUT):
        
        _teacher_index_cache = create_teacher_schedule_index()
        _teacher_index_cache_time = current_time
        print(f"✅ Создан индекс для {len(_teacher_index_cache)} учителей")
    
    return _teacher_index_cache

def parse_time(time_str):
    """Парсит время для сортировки."""
    try:
        # Извлекаем время начала (первая часть до тире)
        start_time = time_str.split('–')[0].split('-')[0].strip()
        
        # Пробуем разные форматы
        if ':' in start_time:
            hours, minutes = map(int, start_time.split(':'))
            return hours * 60 + minutes
        elif '.' in start_time:
            hours, minutes = map(int, start_time.split('.'))
            return hours * 60 + minutes
        else:
            # Если просто число (например, "1" для первого урока)
            lesson_number = int(start_time.split('.')[0])
            return lesson_number * 45
    except:
        return 0

def get_schedule_by_teacher(teacher_name):
    """Получает расписание для конкретного учителя."""
    teacher_index = get_cached_teacher_index()
    
    # Поиск учителя (регистронезависимый)
    teacher_name_lower = teacher_name.lower()
    
    exact_matches = []
    partial_matches = []
    
    for teacher_key, lessons in teacher_index.items():
        # Точное совпадение (игнорируя регистр)
        if teacher_name_lower == teacher_key.lower():
            exact_matches.append({
                'teacher': teacher_key,
                'lessons': lessons,
                'match_type': 'exact'
            })
        # Частичное совпадение
        elif teacher_name_lower in teacher_key.lower():
            partial_matches.append({
                'teacher': teacher_key,
                'lessons': lessons,
                'match_type': 'partial'
            })
    
    # Если есть точные совпадения, используем их
    if exact_matches:
        # Объединяем все уроки из точных совпадений
        all_lessons = []
        for match in exact_matches:
            all_lessons.extend(match['lessons'])
        
        # Удаляем дубликаты (если урок попал к нескольким учителям)
        unique_lessons = remove_duplicate_lessons(all_lessons)
        
        # Сортируем по времени
        sorted_lessons = sorted(unique_lessons, key=lambda x: parse_time(x['time']))
        
        return {
            'teacher': teacher_name,
            'lessons': sorted_lessons,
            'total_lessons': len(sorted_lessons),
            'found_as': exact_matches[0]['teacher'],
            'match_type': 'exact'
        }
    
    # Если есть частичные совпадения
    elif partial_matches:
        # Если несколько частичных совпадений, объединяем
        if len(partial_matches) > 1:
            all_lessons = []
            for match in partial_matches:
                all_lessons.extend(match['lessons'])
            
            unique_lessons = remove_duplicate_lessons(all_lessons)
            sorted_lessons = sorted(unique_lessons, key=lambda x: parse_time(x['time']))
            
            teacher_names = [m['teacher'] for m in partial_matches]
            
            return {
                'teacher': teacher_name,
                'lessons': sorted_lessons,
                'total_lessons': len(sorted_lessons),
                'found_as': f"несколько ({', '.join(teacher_names)})",
                'match_type': 'multiple'
            }
        else:
            # Одно частичное совпадение
            sorted_lessons = sorted(partial_matches[0]['lessons'], 
                                   key=lambda x: parse_time(x['time']))
            
            return {
                'teacher': teacher_name,
                'lessons': sorted_lessons,
                'total_lessons': len(sorted_lessons),
                'found_as': partial_matches[0]['teacher'],
                'match_type': 'partial'
            }
    
    return None

def remove_duplicate_lessons(lessons):
    """Удаляет дубликаты уроков."""
    seen = set()
    unique_lessons = []
    
    for lesson in lessons:
        # Создаем уникальный ключ для урока
        lesson_key = (
            lesson.get('time', ''),
            lesson.get('subject', ''),
            lesson.get('class_name', ''),
            lesson.get('classroom', '')
        )
        
        if lesson_key not in seen:
            seen.add(lesson_key)
            unique_lessons.append(lesson)
    
    return unique_lessons


def search_teachers_by_substring(substring):
    """Ищет учителей по подстроке в фамилии."""
    teacher_index = get_cached_teacher_index()
    substring_lower = substring.lower()
    
    matches = []
    for teacher_name, lessons in teacher_index.items():
        if substring_lower in teacher_name.lower() and lessons:
            # Проверяем, не является ли это составным учителем
            if '/' in teacher_name or '\\' in teacher_name:
                individual_teachers = re.split(r'[\\\/]+', teacher_name)
                main_teacher = individual_teachers[0].strip() if individual_teachers else teacher_name
            else:
                main_teacher = teacher_name
            
            # Если уже есть этот учитель в результатах, объединяем уроки
            existing_match = None
            for match in matches:
                if match['name'] == main_teacher:
                    existing_match = match
                    break
            
            if existing_match:
                existing_match['lesson_count'] += len(lessons)
            else:
                matches.append({
                    'name': main_teacher,
                    'full_name': teacher_name,
                    'lesson_count': len(lessons),
                    'sample_lesson': lessons[0] if lessons else None,
                    'is_combined': '/' in teacher_name or '\\' in teacher_name
                })
    
    # Сортируем по количеству уроков
    matches.sort(key=lambda x: x['lesson_count'], reverse=True)
    
    return matches

def format_teacher_schedule(teacher_info):
    """Форматирует расписание учителя для вывода."""
    if not teacher_info:
        return "❌ Учитель не найден"
    
    teacher_name = teacher_info['teacher']
    lessons = teacher_info['lessons']
    found_as = teacher_info.get('found_as', teacher_name)
    match_type = teacher_info.get('match_type', 'exact')
    
    if not lessons:
        return f"📭 У учителя *{teacher_name}* нет уроков в расписании"
    
    message = f"👨‍🏫 *Расписание учителя {teacher_name}:*\n"
    
    # Добавляем информацию о том, как найден учитель
    if match_type == 'partial' and found_as != teacher_name:
        message += f"(найдено как: *{found_as}*)\n"
    elif match_type == 'multiple':
        message += f"(объединено из: *{found_as}*)\n"
    
    message += "\n"
    
    # Группируем уроки по дням
    lessons_by_day = defaultdict(list)
    for lesson in lessons:
        day = lesson.get('day_section', 'Расписание')
        lessons_by_day[day].append(lesson)
    
    # Выводим по дням
    for day, day_lessons in sorted(lessons_by_day.items()):
        message += f"*{day}:*\n"
        
        for i, lesson in enumerate(day_lessons, 1):
            time_display = lesson['time'].replace('–', '-')
            
            lesson_text = f"{i}. {time_display} - "
            
            if lesson['subject']:
                lesson_text += f"*{lesson['subject']}*"
            
            if lesson['class_name']:
                lesson_text += f" ({lesson['class_name']})"
            
            classroom = lesson.get('classroom', '')
            if classroom and classroom.upper() not in ['ДИСТАНТ', 'дистант', 'ДИСТАНЦИОННО']:
                # Обрабатываем кабинеты через слэш
                if '/' in classroom or '\\' in classroom:
                    classroom_display = classroom.replace('\\', '/')
                else:
                    classroom_display = classroom
                
                lesson_text += f" каб. {classroom_display}"
            
            message += f"  {lesson_text}\n"
        
        message += "\n"
    
    message += f"📊 Всего уроков: {len(lessons)}"
    
    return message

def format_teachers_search_results(matches, search_query):
    """Форматирует результаты поиска учителей."""
    if not matches:
        return f"❌ Учителя с фамилией содержащей '*{search_query}*' не найдены."
    
    message = f"🔍 *Найдено учителей ({len(matches)}):*\n\n"
    
    for i, match in enumerate(matches[:15], 1):
        lesson_sample = match['sample_lesson']
        sample_info = ""
        
        if lesson_sample:
            if lesson_sample.get('subject'):
                subject = lesson_sample['subject'][:20] + ('...' if len(lesson_sample['subject']) > 20 else '')
                sample_info = f" - {subject}"
            if lesson_sample.get('class_name'):
                sample_info += f" ({lesson_sample['class_name']})"
        
        # Добавляем отметку о составном учителе
        teacher_display = match['name']
        if match.get('is_combined', False) and match['full_name'] != match['name']:
            teacher_display += f" ({match['full_name'].replace('/', '/')})"
        
        message += f"{i}. *{teacher_display}* - {match['lesson_count']} уроков{sample_info}\n"
    
    if len(matches) > 15:
        message += f"\n... и еще {len(matches) - 15}"
    
    message += "\n\n💡 Используйте /teacher <фамилия> для подробного расписания"
    
    return message

# === Старые функции (для обратной совместимости) ===

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
    """Получает расписание для класса (старая функция)"""
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
    
    # Сбрасываем кэш учителей
    global _teacher_index_cache, _teacher_index_cache_time
    _teacher_index_cache = None
    _teacher_index_cache_time = None
    
    return lines

def has_schedule_file():
    """Проверяет наличие файла расписания"""
    try:
        with open('school_schedule.csv', 'r', encoding='utf-8'):
            return True
    except FileNotFoundError:
        return False