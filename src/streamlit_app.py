import asyncio
import nest_asyncio
import streamlit as st
import pandas as pd

from service.order_history_service import get_order_histories

# Allow nested event loops and run the async loader
nest_asyncio.apply()
data = asyncio.get_event_loop().run_until_complete(get_order_histories())

df = pd.DataFrame.from_records([row.__dict__ for row in data]).drop(columns=['_sa_instance_state'], errors='ignore')

st.write("Got lots of data? Great! Streamlit can show [dataframes](https://docs.streamlit.io/develop/api-reference/data) with hundred thousands of rows, images, sparklines – and even supports editing! ✍️")

config = {
    "Preview": st.column_config.ImageColumn(),
    "Progress": st.column_config.ProgressColumn(),
}

st.dataframe(df, column_config=config, use_container_width=True)
