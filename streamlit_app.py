
import streamlit as st
import pandas as pd

st.title("Анализ данных с использованием Streamlit")

st.header("Шаг 1: Загрузка данных")

uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    st.write("Превью данных:")
    st.dataframe(data)

    options = data.city.unique()
    selected_option = st.selectbox("Выберите опцию:", options)

else:
    st.write("Пожалуйста, загрузите CSV-файл.")
