import asyncio
import dataclasses

import nest_asyncio
import streamlit as st
import pandas as pd

from service.order_history_service import get_order_histories

# Allow nested event loops and run the async loader
nest_asyncio.apply()

@dataclasses.dataclass
class FetchResult:
    """
    A dataclass to hold the result of the fetch operation.
    """
    order_histories: pd.DataFrame

async def fetch_async_data():
    """
    Asynchronously fetches order histories and returns them as a FetchResult dataclass.
    """

    results = await asyncio.gather(*[
        get_order_histories()
    ])

    results = [*map(lambda models: pd.DataFrame.from_records([row.__dict__ for row in models]).drop(columns=['_sa_instance_state'], errors='ignore'), results)]

    return FetchResult(
        order_histories=results[0]
    )

data: FetchResult = asyncio.get_event_loop().run_until_complete(fetch_async_data())

df = data.order_histories

st.write("Got lots of data? Great! Streamlit can show [dataframes](https://docs.streamlit.io/develop/api-reference/data) with hundred thousands of rows, images, sparklines – and even supports editing! ✍️")

config = {
    "Preview": st.column_config.ImageColumn(),
    "Progress": st.column_config.ProgressColumn(),
}

st.dataframe(df, column_config=config, use_container_width=True)
