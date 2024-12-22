
import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import httpx
import time
from sklearn.linear_model import LinearRegression


month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

#Если использовать асинхронный вызов то температура приходит в цельсиях, если синхронный то в Кельвинах.
async def get_temp(selected_city, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={selected_city}&appid={api_key}&units=metric"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code  == 200:
            response = response.json()
            return response['main']['temp']
        elif response.status_code == 401:
            st.error(response.text)
            return False


def analize_city(city, data):
    city_data = data[data['city'] == city].copy()
    city_data['30_day_mean'] = city_data['temperature'].rolling(window=30, center=True).mean()
    city_data['30_day_std'] = city_data['temperature'].rolling(window=30, center=True).std()
    threshold = 2
    city_data['anomaly'] = ((city_data['temperature'] > city_data['30_day_mean'] + threshold * city_data['30_day_std']) |
                 (city_data['temperature'] < city_data['30_day_mean'] - threshold * city_data['30_day_std']))
    
    city_seasons = city_data[['season', 'temperature']].groupby('season').agg(
    mean_temp = ('temperature', 'mean'),
    std_temp = ('temperature', 'std'),
    min_temp = ('temperature', 'min'),
    max_temp = ('temperature', 'max')
    )
    
    city_data['year'] = city_data['timestamp'].dt.year
    trend_per_year = []
    for year, group in city_data.groupby('year'):
        group['timestamp_days'] = (group['timestamp'] - group['timestamp'].min()).dt.days
        X = group['timestamp_days'].values.reshape(-1, 1)
        y = group['temperature'].values
        model = LinearRegression()
        model.fit(X, y)

        trend_per_year.append({
            'year': year,
            'trend': "положительный" if model.coef_[0] > 0 else "отрицательный" if model.coef_[0] < 0 else "плоский"
        })
        
    trend_per_season = []
    for season, group in city_data.groupby('season'):
        group['timestamp_days'] = (group['timestamp'] - group['timestamp'].min()).dt.days
        X = group['timestamp_days'].values.reshape(-1, 1)
        y = group['temperature'].values
        model = LinearRegression()
        model.fit(X, y)

        trend_per_season.append({
            'season': season,
            'trend': "положительный" if model.coef_[0] > 0 else "отрицательный" if model.coef_[0] < 0 else "плоский"
        })
    
    trend_per_year = pd.DataFrame(trend_per_year).sort_values(by='year')
    trend_per_season = pd.DataFrame(trend_per_season).sort_values(by='season')
    city_seasons['trend'] = trend_per_season.groupby('season').first()
    
    return {
        'city_seasons': city_seasons,
        'trend_per_year': trend_per_year,
        'anomalies': city_data[city_data['anomaly'] == True]
    }


async def main():
    st.title("Анализ температурных данных и мониторинг текущей температуры")

    st.header("Загрузка исторических данных")

    uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])

    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        st.write("Превью данных:")
        st.dataframe(data)
        cities = data.city.unique()
        
        selected_city = st.selectbox("Выберите город:", cities)
        response_for_city = analize_city(selected_city, data)
        st.subheader(f"Аномалии температуры города {selected_city}")
        st.dataframe(response_for_city['anomalies'])

        fig = px.line(data[data['city']==selected_city], x='timestamp', y='temperature', title=f"Температура в {selected_city}")
        fig.add_scatter(x=response_for_city['anomalies']['timestamp'], y=response_for_city['anomalies']['temperature'], mode='markers', marker=dict(color='red'),
                        name="Аномалии")

        plot_key = f"{selected_city}_temperature_plot_{int(time.time())}"
        st.plotly_chart(fig, key=plot_key)

        st.subheader(f"Сезонный профиль для города {selected_city}")
        st.dataframe(response_for_city['city_seasons'])    

        st.subheader(f"Годовые тренды для города {selected_city}")
        st.dataframe(response_for_city['trend_per_year'])    

        api_key = st.text_input("Введите API ключ:")

        if api_key:
            current_temp = await get_temp(selected_city, api_key)
            if current_temp:
                current_season = month_to_season[pd.to_datetime('today').month]
                mean_temp = response_for_city['city_seasons']['mean_temp'].mean()
                min_temp = response_for_city['city_seasons']['min_temp'].min()
                max_temp = response_for_city['city_seasons']['max_temp'].max()
                trend = response_for_city['city_seasons']['trend'].describe()['top']
                normal_temp = response_for_city['city_seasons']['mean_temp'][current_season]
                std_dev = response_for_city['city_seasons']['std_temp'][current_season]
                st.subheader(f"Температура в городе {selected_city}")
                
                st.write(f"Средняя температура: {round(mean_temp,2)}°C")
                st.write(f"Минимальная температура: {round(min_temp,2)}°C")
                st.write(f"Максимальная температура: {round(max_temp,2)}°C")
                st.write(f"Общий тренд: {trend}")
                st.write(f"Текущая температура в {selected_city}: {round(current_temp,2)}°C")
                
                if abs(current_temp - normal_temp) > 2 * std_dev:
                    st.warning(
                        f"Текущая температура в {selected_city} отклоняется от нормы для сезона {current_season}.")
                else:
                    st.success(
                        f"Текущая температура в {selected_city} соответствует нормам для сезона {current_season}.")
                
                

    else:
        st.write("Пожалуйста, загрузите CSV-файл.")


if __name__ == "__main__":
    asyncio.run(main())