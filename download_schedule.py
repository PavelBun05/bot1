import requests
from bs4 import BeautifulSoup
import csv
import logging

logger = logging.getLogger(__name__)

def download_schedule_from_site():
    """Скачивает расписание с сайта и сохраняет в CSV"""
    
    base_url = "http://www.dnevnik25.ru/"
    schedule_url = base_url + "расписание.files/sheet001.htm"
    
    logger.info(f"🌐 Скачиваю расписание с: {schedule_url}")
    
    try:
        response = requests.get(schedule_url, timeout=30)
        response.encoding = 'windows-1251'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        
        if not table:
            logger.error("❌ Таблица не найдена")
            return
        
        with open('school_schedule.csv', 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True, separator=' ') for cell in cells]
                if row_data:
                    writer.writerow(row_data)
            
            logger.info(f"✅ Сохранено {len(rows)} строк")
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        