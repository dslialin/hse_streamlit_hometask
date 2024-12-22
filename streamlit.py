import streamlit as st
import pandas as pd
import numpy as np
import requests
import altair as alt

st.title("Анализ исторических данных о температуре")

uploaded_file = st.file_uploader("Загрузите CSV-файл с историческими данными", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    cities = sorted(df["city"].unique())
    city_choice = st.selectbox("Выберите город", cities)
    api_key = st.text_input("Введите ваш API Key OpenWeatherMap (опционально)", type="password")
    filtered = df[df["city"] == city_choice].copy()
    if len(filtered) > 0:
        grouped_stats = filtered.groupby(["city", "season"])["temperature"].agg(["mean", "std"]).reset_index()
        grouped_stats.columns = ["city", "season", "mean_temp", "std_temp"]
        merged = pd.merge(filtered, grouped_stats, on=["city", "season"], how="left")
        merged["is_anomaly"] = (merged["temperature"] < merged["mean_temp"] - 2 * merged["std_temp"]) | \
                               (merged["temperature"] > merged["mean_temp"] + 2 * merged["std_temp"])
        st.subheader("Описательная статистика")
        st.write(filtered.describe())

        st.subheader("Временной ряд с аномалиями")
        base = alt.Chart(merged).encode(x="timestamp:T", y="temperature:Q")
        normal_line = base.mark_line(color="blue").transform_filter("datum.is_anomaly == false")
        anomaly_points = base.mark_circle(color="red").transform_filter("datum.is_anomaly == true")
        st.altair_chart((normal_line + anomaly_points).interactive(), use_container_width=True)

        st.subheader("Сезонный профиль (среднее и стандартное отклонение)")
        bars = alt.Chart(grouped_stats[grouped_stats["city"] == city_choice]).mark_bar().encode(
            x="season:N",
            y="mean_temp:Q",
            color="season:N"
        )
        error_bars = alt.Chart(grouped_stats[grouped_stats["city"] == city_choice]).mark_errorbar().encode(
            x="season:N",
            y=alt.Y("mean_temp:Q"),
            yError="std_temp:Q"
        )
        st.altair_chart((bars + error_bars).interactive(), use_container_width=True)

        if api_key:
            current_month = pd.Timestamp.now().month
            month_to_season = {12: "winter", 1: "winter", 2: "winter",
                               3: "spring", 4: "spring", 5: "spring",
                               6: "summer", 7: "summer", 8: "summer",
                               9: "autumn", 10: "autumn", 11: "autumn"}
            current_season = month_to_season[current_month]
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": city_choice,
                "appid": api_key,
                "units": "metric"
            }
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                data_json = resp.json()
                current_temp = data_json["main"]["temp"]
                row = grouped_stats[(grouped_stats["city"] == city_choice) & (grouped_stats["season"] == current_season)]
                if len(row) > 0:
                    mean_t = row["mean_temp"].values[0]
                    std_t = row["std_temp"].values[0]
                    low = mean_t - 2 * std_t
                    high = mean_t + 2 * std_t
                    if low <= current_temp <= high:
                        st.write("Текущая температура в норме:", current_temp, "°C")
                    else:
                        st.write("Текущая температура аномальная:", current_temp, "°C")
                else:
                    st.write("Нет данных по текущему сезону в исторической выборке.")
            else:
                if resp.status_code == 401:
                    st.error("Неверный API ключ OpenWeatherMap.")
                else:
                    st.error(f"Ошибка при получении данных (код {resp.status_code}).")