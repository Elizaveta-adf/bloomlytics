import os
import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from faker import Faker
import numpy as np

# Загружаем переменные окружения из .env
load_dotenv()

# Подключаемся к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найдена в .env файле!")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Инициализируем генератор случайных данных
fake = Faker('ru_RU')  # Русскоязычные данные
random.seed(42)        # Для воспроизводимости
np.random.seed(42)

# --- 1. Очищаем таблицы перед загрузкой (чтобы не было дублей) ---
print("🧹 Очищаем таблицы...")
cur.execute("TRUNCATE TABLE orders, marketing_spend, florists RESTART IDENTITY CASCADE;")
conn.commit()

# --- 2. Генерируем флористов (5-8 человек) ---
print("🌷 Генерируем флористов...")
florists = []
florist_names = [
    "Анна Смирнова", "Екатерина Иванова", "Мария Петрова", 
    "Ольга Сидорова", "Наталья Кузнецова", "Дарья Попова",
    "Светлана Соколова", "Елена Михайлова"
]

for i, name in enumerate(florist_names[:random.randint(5, 8)], start=1):
    hourly_rate = round(random.uniform(300, 600), 2)
    hire_date = fake.date_between(start_date='-2y', end_date='today')
    florists.append({
        "florist_id": i,
        "name": name,
        "hourly_rate": hourly_rate,
        "hire_date": hire_date
    })
    cur.execute("""
        INSERT INTO florists (name, hourly_rate, hire_date)
        VALUES (%s, %s, %s)
    """, (name, hourly_rate, hire_date))

conn.commit()
print(f"✅ Добавлено {len(florists)} флористов")

# --- 3. Генерируем маркетинговые расходы (за последние 3 месяца) ---
print("📊 Генерируем маркетинговые расходы...")
end_date = datetime.now().date()
start_date = end_date - timedelta(days=90)

channels = ['instagram', 'telegram', 'yandex', 'vk', 'organic']
marketing_data = []

current_date = start_date
while current_date <= end_date:
    for channel in channels:
        # organic — бесплатный канал
        if channel == 'organic':
            cost = 0
            clicks = random.randint(50, 200)
            impressions = random.randint(500, 2000)
        else:
            # В пиковые дни (8 марта, 14 февраля) расходы выше
            if (current_date.month == 3 and current_date.day == 8) or \
               (current_date.month == 2 and current_date.day == 14):
                cost = random.randint(5000, 15000)
            # В обычные дни — меньше
            else:
                cost = random.randint(1000, 5000)
            
            # В выходные расходы выше
            if current_date.weekday() >= 5:  # суббота, воскресенье
                cost = cost * 1.3
            
            clicks = random.randint(100, 500)
            impressions = random.randint(1000, 5000)
        
        marketing_data.append({
            "date": current_date,
            "utm_source": channel,
            "clicks": clicks,
            "impressions": impressions,
            "cost": round(cost, 2)
        })
        
        cur.execute("""
            INSERT INTO marketing_spend (date, utm_source, clicks, impressions, cost)
            VALUES (%s, %s, %s, %s, %s)
        """, (current_date, channel, clicks, impressions, round(cost, 2)))
    
    current_date += timedelta(days=1)

conn.commit()
print(f"✅ Добавлено {len(marketing_data)} записей о маркетинговых расходах")

# --- 4. Генерируем заказы (500-1000 штук) ---
print("💐 Генерируем заказы...")
num_orders = random.randint(500, 1000)
orders = []
florist_ids = [f["florist_id"] for f in florists]

statuses = ['completed', 'completed', 'completed', 'completed', 'cancelled']  # 80% выполнено

for _ in range(num_orders):
    # Случайная дата за последние 3 месяца
    created_at = fake.date_time_between(start_date=start_date, end_date=end_date)
    
    # Сумма заказа
    # В праздники — больше
    if (created_at.month == 3 and created_at.day == 8) or \
       (created_at.month == 2 and created_at.day == 14):
        total_amount = round(random.uniform(3000, 15000), 2)
    # В обычные дни
    else:
        total_amount = round(random.uniform(1000, 8000), 2)
    
    # Скидка (0-20% редко, 0-5% часто)
    if random.random() < 0.1:  # 10% заказов со скидкой
        discount_amount = round(total_amount * random.uniform(0.05, 0.20), 2)
    else:
        discount_amount = 0
    
    # Себестоимость (40-70% от цены)
    cost_price = round(total_amount * random.uniform(0.40, 0.70), 2)
    
    # Флорист
    florist_id = random.choice(florist_ids)
    
    # Статус
    status = random.choice(statuses)
    
    # Время сборки (15-60 минут)
    assembly_time = random.randint(15, 60)
    
    # Оценка клиента (1-5), если заказ выполнен
    if status == 'completed':
        client_rating = random.randint(3, 5)  # чаще высокие оценки
    else:
        client_rating = None
    
    # Канал привлечения
    utm_source = random.choices(
        ['instagram', 'telegram', 'yandex', 'vk', 'organic'],
        weights=[0.30, 0.20, 0.15, 0.15, 0.20]  # Instagram — самый популярный
    )[0]
    
    orders.append({
        "created_at": created_at,
        "status": status,
        "total_amount": total_amount,
        "discount_amount": discount_amount,
        "cost_price": cost_price,
        "florist_id": florist_id,
        "assembly_time_minutes": assembly_time if status == 'completed' else None,
        "client_rating": client_rating,
        "utm_source": utm_source
    })
    
    cur.execute("""
        INSERT INTO orders (created_at, status, total_amount, discount_amount, 
                            cost_price, florist_id, assembly_time_minutes, 
                            client_rating, utm_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (created_at, status, total_amount, discount_amount, 
          cost_price, florist_id, 
          assembly_time if status == 'completed' else None,
          client_rating, utm_source))

conn.commit()
print(f"✅ Добавлено {len(orders)} заказов")

# --- 5. Проверка: сколько данных загружено ---
print("\n📊 Статистика загрузки:")
cur.execute("SELECT COUNT(*) FROM florists")
print(f"  👤 Флористов: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM orders")
print(f"  💐 Заказов: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM marketing_spend")
print(f"  📊 Маркетинговых записей: {cur.fetchone()[0]}")

# Закрываем соединение
cur.close()
conn.close()
print("\n🎉 Готово! База данных заполнена демо-данными.")