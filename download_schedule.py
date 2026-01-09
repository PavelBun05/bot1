import requests
from bs4 import BeautifulSoup
import csv

def download_schedule_from_site():
    """Скачивает расписание с сайта и сохраняет в CSV"""
    
    # URL расписания
    base_url = "http://www.dnevnik25.ru/"
    schedule_url = base_url + "расписание.files/sheet001.htm"
    
    print(f"🌐 Скачиваю расписание с: {schedule_url}")
    
    try:
        # Загружаем HTML
        response = requests.get(schedule_url, timeout=15)
        response.encoding = 'windows-1251'
        html_content = response.text
        
        print("✅ HTML успешно загружен")
        
        # Парсим HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Находим таблицу
        table = soup.find('table')
        
        if not table:
            print("❌ Таблица не найдена на странице")
            return
        
        print(f"✅ Таблица найдена")
        
        # Создаем CSV файл
        with open('school_schedule.csv', 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Проходим по всем строкам таблицы
            rows = table.find_all('tr')
            print(f"📊 Найдено строк: {len(rows)}")
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                row_data = []
                
                for cell in cells:
                    cell_text = cell.get_text(strip=True, separator=' ')
                    cell_text = ' '.join(cell_text.split())
                    row_data.append(cell_text)
                
                if row_data:
                    writer.writerow(row_data)
            
            print(f"\n💾 Все данные сохранены в файл: school_schedule.csv")
            
    except Exception as e:
        print(f"❌ Ошибка при загрузке: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 ТЕСТ: Загрузка расписания")
    print("=" * 60)
    download_schedule_from_site()