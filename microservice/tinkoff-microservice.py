import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from collections import defaultdict, deque
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import tinvest
import yfinance as yf

from custom_index import CustomIndex


api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ci = CustomIndex()

@api.get('/api/historical_candles/{days}')
def historical_candles(days: int):
    global ci

    # Средняя цена
    d = defaultdict(pd.DataFrame)

    def concat_columns(d, candles_one):
        for col in ['open', 'high', 'low', 'close']:
            d[col] = pd.concat([d[col], candles_one[col]], axis=1)

        return d        

    try:
        # tinkoff historical data
        for _, row in ci.df.iterrows():
            candles_one = ci.get_tinkoff_candles(row['figi'], days)
            candles_one *= row['portion']
            d = concat_columns(d, candles_one)

        # # yahoo historical data
        # for _, row in ci.df_yahoo.iterrows():
        #     candles_one = ci.get_yahoo_candles(row['ticker'], days)
        #     candles_one *= row['portion']
        #     d = concat_columns(d, candles_one)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

            
    for col in ['open', 'high', 'low', 'close']:
        d[col] = d[col].sort_index(ascending=True)
        d[col] = d[col].fillna(method='ffill')
        d[col] = d[col].dropna()
        d[col] = d[col].sum(axis=1) / 100

    candles = pd.DataFrame(d)

    candles.index.name = 'time'
    candles.reset_index(inplace=True)


    return candles.to_json(orient="records")


# Запускать раз в 5 секунд
# https://tinkoff.github.io/invest-openapi/rest/
@api.get('/api/currient_candle')
def currient_candle():
    global ci

    curr_time = ci.round_to_5min(pd.Timestamp.now(tz='Europe/Moscow'))

    try:
        last_price = ci.get_last_price()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # формирование свечей по последней цене
    if curr_time > ci.last_candle['time']:
        # Новая свеча
        ci.last_candle = pd.Series({'open': last_price, 
                                    'high': last_price, 
                                    'low': last_price, 
                                    'close': last_price, 
                                    'time': curr_time})
    else:
        ci.last_candle['close'] = last_price

        if ci.last_candle['high'] < last_price:
            ci.last_candle['high'] = last_price

        elif ci.last_candle['low'] > last_price:
            ci.last_candle['low'] = last_price
    
    
    return ci.last_candle.to_json()


