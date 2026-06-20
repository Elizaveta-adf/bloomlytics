-- ============================================================
-- BLOOMLYTICS — SQL-ЗАПРОСЫ ДЛЯ МЕТРИК
-- Проект: Сквозная аналитика цветочного магазина
-- База данных: PostgreSQL (Neon.tech)
-- ============================================================

-- ============================================================
-- 1. ФИНАНСОВЫЕ МЕТРИКИ (таблица orders)
-- ============================================================

-- 1.1 Общая выручка и количество заказов
-- Для карточек "Выручка" и "Количество заказов"
SELECT 
    SUM(total_amount) AS total_revenue,
    COUNT(*) AS total_orders
FROM orders
WHERE status = 'completed';

-- 1.2 Чистая прибыль
-- Для карточки "Прибыль" (выручка минус себестоимость)
SELECT 
    SUM(total_amount - cost_price) AS net_profit,
    ROUND(AVG(total_amount - cost_price), 2) AS avg_profit_per_order
FROM orders
WHERE status = 'completed';

-- 1.3 Средний чек (AOV)
-- Для карточки "Средний чек"
SELECT 
    ROUND(AVG(total_amount), 2) AS average_order_value
FROM orders
WHERE status = 'completed';

-- 1.4 Процент отмен
-- Для карточки "% отмен" — показывает долю недоставленных заказов
SELECT 
    ROUND(
        100.0 * COUNT(CASE WHEN status = 'cancelled' THEN 1 END) / COUNT(*), 
        2
    ) AS cancellation_rate_percent
FROM orders;

-- 1.5 Динамика выручки по месяцам (MoM)
-- Для графика "Выручка по месяцам" — показывает сезонность
SELECT 
    DATE_TRUNC('month', created_at) AS month,
    SUM(total_amount) AS revenue,
    COUNT(*) AS orders_count,
    ROUND(AVG(total_amount), 2) AS avg_check
FROM orders
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;

-- 1.6 Топ-5 дней по выручке (сезонные пики)
-- Для инсайта: "8 марта — пик выручки"
SELECT 
    DATE(created_at) AS day,
    SUM(total_amount) AS revenue,
    COUNT(*) AS orders_count
FROM orders
WHERE status = 'completed'
GROUP BY DATE(created_at)
ORDER BY revenue DESC
LIMIT 5;

-- 1.7 Средний чек по дням недели
-- Для инсайта: "Пятница — лучший день для продаж"
SELECT 
    TO_CHAR(created_at, 'Day') AS weekday,
    ROUND(AVG(total_amount), 2) AS avg_check,
    COUNT(*) AS orders_count
FROM orders
WHERE status = 'completed'
GROUP BY TO_CHAR(created_at, 'Day')
ORDER BY avg_check DESC;

-- ============================================================
-- 2. МАРКЕТИНГОВЫЕ МЕТРИКИ (orders + marketing_spend)
-- ============================================================

-- 2.1 CAC, ROAS, выручка по каналам
-- Главный маркетинговый запрос — окупаемость каждого канала
WITH marketing_metrics AS (
    SELECT 
        o.utm_source,
        COUNT(DISTINCT o.order_id) AS orders_count,
        SUM(m.cost) AS total_marketing_cost,
        SUM(o.total_amount) AS revenue_from_channel
    FROM orders o
    JOIN marketing_spend m ON o.utm_source = m.utm_source
        AND DATE(o.created_at) = m.date
    WHERE o.status = 'completed'
    GROUP BY o.utm_source
)
SELECT 
    utm_source,
    orders_count,
    total_marketing_cost,
    ROUND(total_marketing_cost / NULLIF(orders_count, 0), 2) AS cac,
    ROUND(revenue_from_channel, 2) AS revenue,
    ROUND(revenue_from_channel / NULLIF(total_marketing_cost, 0), 2) AS roas
FROM marketing_metrics
ORDER BY roas DESC;

-- 2.2 Общий ROMI (Return on Marketing Investment)
-- Для карточки "ROMI" — общая эффективность маркетинга
SELECT 
    ROUND(
        (SUM(o.total_amount) - SUM(m.cost)) / NULLIF(SUM(m.cost), 0) * 100, 
        2
    ) AS romi_percent,
    SUM(o.total_amount) AS total_revenue,
    SUM(m.cost) AS total_marketing_cost
FROM orders o
JOIN marketing_spend m ON DATE(o.created_at) = m.date
WHERE o.status = 'completed';

-- 2.3 Динамика расходов на маркетинг по дням
-- Для графика "Маркетинговые расходы по дням"
SELECT 
    date,
    utm_source,
    cost,
    clicks,
    impressions
FROM marketing_spend
ORDER BY date DESC
LIMIT 30;

-- 2.4 Сводка по каналам: сколько заказов и выручки
-- Для таблицы "Эффективность каналов"
SELECT 
    utm_source,
    COUNT(*) AS orders_count,
    SUM(total_amount) AS revenue,
    ROUND(AVG(total_amount), 2) AS avg_check
FROM orders
WHERE status = 'completed'
GROUP BY utm_source
ORDER BY revenue DESC;

-- ============================================================
-- 3. KPI ФЛОРИСТОВ (orders + florists)
-- ============================================================

-- 3.1 Основные KPI флористов
-- Для таблицы "Эффективность сотрудников"
SELECT 
    f.name AS florist_name,
    COUNT(o.order_id) AS bouquets_made,
    ROUND(AVG(o.total_amount), 2) AS avg_bouquet_price,
    ROUND(AVG(o.assembly_time_minutes), 0) AS avg_assembly_time_min,
    ROUND(AVG(o.client_rating), 2) AS avg_rating,
    SUM(o.total_amount) AS total_revenue
FROM florists f
JOIN orders o ON f.florist_id = o.florist_id
WHERE o.status = 'completed'
GROUP BY f.florist_id, f.name
ORDER BY total_revenue DESC;

-- 3.2 Выручка на флориста
-- Для карточек "Лучший флорист по выручке"
SELECT 
    f.name AS florist_name,
    SUM(o.total_amount) AS total_revenue,
    COUNT(o.order_id) AS bouquets_made,
    ROUND(SUM(o.total_amount) / NULLIF(COUNT(o.order_id), 0), 2) AS revenue_per_bouquet,
    ROUND(AVG(o.assembly_time_minutes), 0) AS avg_time_min
FROM florists f
JOIN orders o ON f.florist_id = o.florist_id
WHERE o.status = 'completed'
GROUP BY f.florist_id, f.name
ORDER BY total_revenue DESC;

-- 3.3 Рейтинг флористов (по оценкам клиентов)
-- Для карточки "Лучший флорист по рейтингу"
SELECT 
    f.name AS florist_name,
    ROUND(AVG(o.client_rating), 2) AS avg_rating,
    COUNT(o.order_id) AS rated_orders
FROM florists f
JOIN orders o ON f.florist_id = o.florist_id
WHERE o.status = 'completed' AND o.client_rating IS NOT NULL
GROUP BY f.florist_id, f.name
ORDER BY avg_rating DESC;

-- 3.4 Сезонная загрузка флористов (по месяцам)
-- Для графика "Загрузка флористов по месяцам"
SELECT 
    f.name AS florist_name,
    DATE_TRUNC('month', o.created_at) AS month,
    COUNT(o.order_id) AS bouquets_made
FROM florists f
JOIN orders o ON f.florist_id = o.florist_id
WHERE o.status = 'completed'
GROUP BY f.florist_id, f.name, DATE_TRUNC('month', o.created_at)
ORDER BY month, bouquets_made DESC;

-- ============================================================
-- 4. СВОДНЫЕ МЕТРИКИ (для главного дашборда)
-- ============================================================

-- 4.1 Главная сводка (все KPI в одной таблице)
-- Для верхней части дашборда — все ключевые цифры в одном месте
SELECT 
    (SELECT SUM(total_amount) FROM orders WHERE status = 'completed') AS total_revenue,
    (SELECT SUM(total_amount - cost_price) FROM orders WHERE status = 'completed') AS net_profit,
    (SELECT ROUND(AVG(total_amount), 2) FROM orders WHERE status = 'completed') AS avg_check,
    (SELECT COUNT(*) FROM orders WHERE status = 'completed') AS total_orders,
    (SELECT ROUND(100.0 * COUNT(CASE WHEN status = 'cancelled' THEN 1 END) / COUNT(*), 2) FROM orders) AS cancellation_rate,
    (SELECT ROUND(AVG(client_rating), 2) FROM orders WHERE status = 'completed' AND client_rating IS NOT NULL) AS avg_rating;

-- 4.2 Выручка, себестоимость и прибыль по месяцам
-- Для графика "Финансовый отчёт по месяцам"
SELECT 
    DATE_TRUNC('month', o.created_at) AS month,
    SUM(o.total_amount) AS revenue,
    SUM(o.cost_price) AS cost_of_goods,
    SUM(o.total_amount - o.cost_price) AS profit
FROM orders o
WHERE o.status = 'completed'
GROUP BY DATE_TRUNC('month', o.created_at)
ORDER BY month;

-- 4.3 Выручка по каналам и флористам (сводная)
-- Для сложного графика "Кто и откуда приносит деньги"
SELECT 
    o.utm_source,
    f.name AS florist_name,
    COUNT(o.order_id) AS orders_count,
    SUM(o.total_amount) AS revenue
FROM orders o
JOIN florists f ON o.florist_id = f.florist_id
WHERE o.status = 'completed'
GROUP BY o.utm_source, f.name
ORDER BY revenue DESC;