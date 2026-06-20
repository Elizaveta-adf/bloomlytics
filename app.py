import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# ============================================================
# 1. НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="Bloomlytics — Аналитика цветочного магазина",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стилизация (тёмная тема как у Spotify Wrapped)
st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #ff6b9d;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1rem;
            color: #888888;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #1e1e2e;
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 4px solid #ff6b9d;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .insight-box {
            background-color: #1e1e2e;
            padding: 1rem 1.5rem;
            border-radius: 10px;
            border-left: 4px solid #fbbf24;
            margin: 0.5rem 0;
        }
        .insight-good {
            border-left-color: #34d399;
        }
        .insight-bad {
            border-left-color: #f87171;
        }
        .stMetric {
            background-color: #1e1e2e;
            padding: 0.8rem;
            border-radius: 10px;
        }
        .florist-card {
            background-color: #1e1e2e;
            padding: 0.8rem 1.2rem;
            border-radius: 8px;
            margin: 0.3rem 0;
            border-left: 3px solid #ff6b9d;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================================
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL)

engine = get_engine()

# ============================================================
# 3. ФУНКЦИИ ЗАГРУЗКИ ДАННЫХ (с кешированием)
# ============================================================
@st.cache_data(ttl=300)
def load_main_metrics():
    """Загружает основные финансовые метрики"""
    query = """
        SELECT 
            (SELECT SUM(total_amount) FROM orders WHERE status = 'completed') AS total_revenue,
            (SELECT SUM(total_amount - cost_price) FROM orders WHERE status = 'completed') AS net_profit,
            (SELECT ROUND(AVG(total_amount), 2) FROM orders WHERE status = 'completed') AS avg_check,
            (SELECT COUNT(*) FROM orders WHERE status = 'completed') AS total_orders,
            (SELECT ROUND(100.0 * COUNT(CASE WHEN status = 'cancelled' THEN 1 END) / COUNT(*), 2) FROM orders) AS cancellation_rate,
            (SELECT ROUND(AVG(client_rating), 2) FROM orders WHERE status = 'completed' AND client_rating IS NOT NULL) AS avg_rating
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

@st.cache_data(ttl=300)
def load_monthly_dynamics():
    """Загружает динамику по месяцам"""
    query = """
        SELECT 
            DATE_TRUNC('month', created_at) AS month,
            SUM(total_amount) AS revenue,
            SUM(cost_price) AS cost_of_goods,
            SUM(total_amount - cost_price) AS profit
        FROM orders
        WHERE status = 'completed'
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

@st.cache_data(ttl=300)
def load_marketing_metrics():
    """Загружает маркетинговые метрики по каналам"""
    query = """
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
        ORDER BY roas DESC
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

@st.cache_data(ttl=300)
def load_florist_kpi():
    """Загружает KPI флористов"""
    query = """
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
        ORDER BY total_revenue DESC
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

@st.cache_data(ttl=300)
def load_daily_dynamics():
    """Загружает дневную динамику для графика"""
    query = """
        SELECT 
            DATE(created_at) AS date,
            SUM(total_amount) AS revenue,
            SUM(cost_price) AS cost_of_goods
        FROM orders
        WHERE status = 'completed'
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

@st.cache_data(ttl=300)
def load_channel_summary():
    """Загружает сводку по каналам"""
    query = """
        SELECT 
            utm_source,
            COUNT(*) AS orders_count,
            SUM(total_amount) AS revenue,
            ROUND(AVG(total_amount), 2) AS avg_check
        FROM orders
        WHERE status = 'completed'
        GROUP BY utm_source
        ORDER BY revenue DESC
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# ============================================================
# 4. САЙДБАР
# ============================================================
st.sidebar.title("🌸 Bloomlytics")
st.sidebar.markdown("---")
st.sidebar.markdown("**Аналитика цветочного магазина**")
st.sidebar.markdown("---")

# Выбор периода (пока просто для демонстрации, в будущем можно добавить фильтр)
period_options = ["Последние 30 дней", "Последние 3 месяца", "Всё время"]
selected_period = st.sidebar.selectbox("📆 Период", period_options)

st.sidebar.markdown("---")
st.sidebar.markdown("**📊 Метрики**")
st.sidebar.markdown("- Финансы")
st.sidebar.markdown("- Маркетинг (ROAS, CAC)")
st.sidebar.markdown("- KPI флористов")

st.sidebar.markdown("---")
st.sidebar.caption("Данные из PostgreSQL (Neon.tech)")

# ============================================================
# 5. ОСНОВНОЙ КОНТЕНТ
# ============================================================

# Заголовок
st.markdown('<p class="main-header">🌸 Bloomlytics</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Сквозная аналитика цветочного магазина — от лида до прибыли</p>', unsafe_allow_html=True)

# --- Загрузка данных ---
with st.spinner("Загрузка данных..."):
    main_metrics = load_main_metrics()
    monthly_data = load_monthly_dynamics()
    marketing_data = load_marketing_metrics()
    florist_data = load_florist_kpi()
    daily_data = load_daily_dynamics()
    channel_data = load_channel_summary()

# --- 5.1 КАРТОЧКИ С МЕТРИКАМИ ---
st.markdown("### 📊 Ключевые показатели")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="💰 Выручка", 
        value=f"{main_metrics['total_revenue'].iloc[0]:,.0f} ₽",
        delta=None
    )
with col2:
    st.metric(
        label="📈 Прибыль", 
        value=f"{main_metrics['net_profit'].iloc[0]:,.0f} ₽"
    )
with col3:
    st.metric(
        label="🛒 Средний чек", 
        value=f"{main_metrics['avg_check'].iloc[0]:,.0f} ₽"
    )
with col4:
    st.metric(
        label="📦 Заказов", 
        value=f"{main_metrics['total_orders'].iloc[0]:,}"
    )
with col5:
    st.metric(
        label="⭐ Рейтинг", 
        value=f"{main_metrics['avg_rating'].iloc[0]:.2f} / 5"
    )

# --- 5.2 ГРАФИК 1: ДИНАМИКА ВЫРУЧКИ И ПРИБЫЛИ ---
st.markdown("---")
st.markdown("### 📈 Динамика выручки и прибыли")

if not daily_data.empty:
    fig1 = px.line(
        daily_data, 
        x='date', 
        y=['revenue', 'cost_of_goods'],
        title="Выручка и себестоимость по дням",
        labels={'value': 'Сумма (₽)', 'date': 'Дата', 'variable': 'Показатель'},
        color_discrete_map={'revenue': '#ff6b9d', 'cost_of_goods': '#fbbf24'}
    )
    fig1.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#ffffff',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig1, use_container_width=True)

# --- 5.3 ДВЕ КОЛОНКИ: Маркетинг + Флористы ---
col_left, col_right = st.columns(2)

# ЛЕВАЯ КОЛОНКА: МАРКЕТИНГ
with col_left:
    st.markdown("### 📢 Маркетинговые метрики")
    
    if not marketing_data.empty:
        # ROAS по каналам (горизонтальные бары)
        fig2 = px.bar(
            marketing_data,
            x='roas',
            y='utm_source',
            orientation='h',
            title="ROAS по каналам",
            labels={'roas': 'ROAS (руб/руб)', 'utm_source': 'Канал'},
            color='roas',
            color_continuous_scale=['#f87171', '#fbbf24', '#34d399'],
            range_color=[0, 5]
        )
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#ffffff',
            height=300
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Таблица маркетинга
        st.dataframe(
            marketing_data[['utm_source', 'orders_count', 'cac', 'roas', 'revenue']],
            column_config={
                'utm_source': 'Канал',
                'orders_count': 'Заказы',
                'cac': st.column_config.NumberColumn('CAC (₽)', format="%.0f"),
                'roas': st.column_config.NumberColumn('ROAS', format="%.2f"),
                'revenue': st.column_config.NumberColumn('Выручка (₽)', format="%.0f")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Нет данных по маркетингу")

# ПРАВАЯ КОЛОНКА: ФЛОРИСТЫ
with col_right:
    st.markdown("### 👤 KPI флористов")
    
    if not florist_data.empty:
        # Таблица флористов
        st.dataframe(
            florist_data,
            column_config={
                'florist_name': 'Флорист',
                'bouquets_made': 'Букетов',
                'avg_bouquet_price': st.column_config.NumberColumn('Ср. цена (₽)', format="%.0f"),
                'avg_assembly_time_min': 'Время (мин)',
                'avg_rating': st.column_config.NumberColumn('Рейтинг', format="%.2f"),
                'total_revenue': st.column_config.NumberColumn('Выручка (₽)', format="%.0f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # График выручки по флористам
        fig3 = px.bar(
            florist_data,
            x='florist_name',
            y='total_revenue',
            title="Выручка по флористам",
            labels={'florist_name': 'Флорист', 'total_revenue': 'Выручка (₽)'},
            color='total_revenue',
            color_continuous_scale=['#fbbf24', '#ff6b9d']
        )
        fig3.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='#ffffff',
            height=250
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Нет данных по флористам")

# --- 5.4 СЕЗОННАЯ ДИНАМИКА (ПО МЕСЯЦАМ) ---
st.markdown("---")
st.markdown("### 📅 Сезонная динамика")

if not monthly_data.empty:
    fig4 = px.bar(
        monthly_data,
        x='month',
        y=['revenue', 'profit'],
        title="Выручка и прибыль по месяцам",
        labels={'value': 'Сумма (₽)', 'month': 'Месяц', 'variable': 'Показатель'},
        barmode='group',
        color_discrete_map={'revenue': '#ff6b9d', 'profit': '#34d399'}
    )
    fig4.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='#ffffff',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig4, use_container_width=True)

# --- 5.5 АВТОМАТИЧЕСКИЕ ИНСАЙТЫ ---
st.markdown("---")
st.markdown("### 🧠 Автоматические инсайты")

# Функция для генерации инсайтов
def generate_insights(main_metrics, marketing_data, florist_data, daily_data):
    insights = []
    
    # 1. Финансовые инсайты
    profit_margin = main_metrics['net_profit'].iloc[0] / main_metrics['total_revenue'].iloc[0] * 100 if main_metrics['total_revenue'].iloc[0] > 0 else 0
    if profit_margin < 40:
        insights.append(("⚠️ Маржинальность ниже 40%", "Проверьте себестоимость и цены на цветы", "bad"))
    elif profit_margin > 55:
        insights.append(("✅ Отличная маржинальность!", "Бизнес эффективен, продолжайте в том же духе", "good"))
    else:
        insights.append(("📊 Маржинальность в норме", "Держите текущий уровень цен и себестоимости", "good"))
    
    # 2. Маркетинговые инсайты
    if not marketing_data.empty:
        best_channel = marketing_data.loc[marketing_data['roas'].idxmax()]
        if best_channel['roas'] > 3:
            insights.append((f"🚀 Лучший канал: {best_channel['utm_source']}", 
                           f"ROAS = {best_channel['roas']:.1f} — вкладывайте сюда больше!", "good"))
        
        worst_channel = marketing_data.loc[marketing_data['roas'].idxmin()]
        if worst_channel['roas'] < 1:
            insights.append((f"⚠️ Худший канал: {worst_channel['utm_source']}", 
                           f"ROAS = {worst_channel['roas']:.1f} — рассмотрите отключение", "bad"))
    
    # 3. Инсайты по флористам
    if not florist_data.empty:
        best_florist = florist_data.loc[florist_data['total_revenue'].idxmax()]
        insights.append((f"🏆 Лучший флорист: {best_florist['florist_name']}", 
                       f"Принёс {best_florist['total_revenue']:,.0f} ₽ — премируйте!", "good"))
        
        # Проверка на медленную сборку
        slow_florists = florist_data[florist_data['avg_assembly_time_min'] > 45]
        for _, row in slow_florists.iterrows():
            insights.append((f"🐌 Медленный флорист: {row['florist_name']}", 
                           f"Среднее время сборки {row['avg_assembly_time_min']:.0f} мин — оптимизируйте процесс", "bad"))
    
    # 4. Сезонный инсайт
    if not daily_data.empty:
        # Находим пиковый день
        peak_day = daily_data.loc[daily_data['revenue'].idxmax()]
        insights.append((f"📈 Пик продаж: {peak_day['date']}", 
                       f"Выручка {peak_day['revenue']:,.0f} ₽ — готовьтесь к таким дням заранее", "good"))
    
    return insights

insights = generate_insights(main_metrics, marketing_data, florist_data, daily_data)

# Отображаем инсайты
for title, description, insight_type in insights:
    if insight_type == "good":
        st.markdown(f"""
            <div class="insight-box insight-good">
                <strong>{title}</strong><br>
                <span style="color: #d4d4d4;">{description}</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="insight-box insight-bad">
                <strong>{title}</strong><br>
                <span style="color: #d4d4d4;">{description}</span>
            </div>
        """, unsafe_allow_html=True)

# --- 5.6 ФУТЕР ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666666; font-size: 0.8rem; padding: 1rem 0;">
    <p>🌸 Bloomlytics — Сквозная аналитика цветочного магазина</p>
    <p>Данные из PostgreSQL (Neon.tech) • Визуализация: Streamlit + Plotly</p>
    <p>Проект выполнен с использованием BPMN, IDEF0 и вайбкодинга</p>
</div>
""", unsafe_allow_html=True)