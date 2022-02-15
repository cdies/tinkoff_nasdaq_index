import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from collections import defaultdict, deque
import httpx
import logging
import sys

import tinvest
import yfinance as yf

import warnings
warnings.filterwarnings("ignore", 'This pattern has match groups')


class CustomIndex:

    def __init__(self, token='token.txt'):
        self.logger = self.__create_logger()

        self.q_tokens = deque()
        try:
            with open(token, 'r') as file:
                for line in file:
                    self.q_tokens.append(line.rstrip())
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> Ошибка в файле token.txt: '+ str(e))

        self.last_candle = pd.Series({'open': 0.0, 
                                      'high': 0.0, 
                                      'low': 0.0, 
                                      'close': 0.0, 
                                      'time': pd.Timestamp(0, tz='Europe/Moscow')})

        try:
            table = pd.read_html('https://www.tinkoff.ru/invest/etfs/TECH/structure/details/')
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> (www.tinkoff.ru) - Ошибка загрузки состава фонда.')        

        df = table[0]
        df = df.rename(columns={'Название': 'name', 'Доля в портфеле': 'portion'})
        df = df[df['name'] != 'Денежные средстваВалюта']
        df['name'] = df['name'].str[:-5]
        df['portion'] = df['portion'].str[:-1]
        df['portion'] = df['portion'].str.replace(',', '.').astype(float)

        client = self.__get_tinkoff_client()

        try:
            all_stocks = pd.DataFrame.from_dict(client.get_market_stocks().dict()['payload']['instruments'])
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> tinkoff api - Ошибка загрузки данных обо всех акциях.')

        df = pd.merge(df, all_stocks, how='left', on='name', sort=True)
        df = df[['name', 'ticker', 'figi', 'portion']]
        df = df[~df['ticker'].str.contains('_old', na=False)]

        df_yahoo = df[df['ticker'].isna()]
        self.df = df[~df['ticker'].isna()]
        
        try:
            table = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> (www.wikipedia.org) - Ошибка загрузки тикетов Nasdaq.')

        df_nasdaq = table[3]
        
        temp = pd.DataFrame()
        for _, row in df_nasdaq.iterrows():
            test = df_yahoo[df_yahoo['name'].str.contains(row['Company'])].copy()
            if len(test) != 0:
                test['ticker'] = row['Ticker']
                temp = temp.append(test)
        
        df_yahoo = temp.drop_duplicates()
        
        if len(df_yahoo) != len(df_yahoo['ticker'].unique()):
            raise Exception('--> There are few same tickets in df_yahoo')
        
        df_yahoo['last_price'] = -1
        self.df_yahoo = df_yahoo


    def round_to_5min(self, t):
        delta = pd.Timedelta(minutes=t.minute%5, 
                            seconds=t.second, 
                            microseconds=t.microsecond)
        t -= delta
               
        return t


    def __create_logger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.ERROR)
        
        formatter = logging.Formatter('--> %(asctime)s - %(name)s - %(levelname)s - %(message)s')

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)    
        logger.addHandler(sh)
        
        # send logs in docker logs
        fh = logging.FileHandler('/proc/1/fd/1')
        fh.setFormatter(formatter)    
        logger.addHandler(fh)

        return logger


    def __get_tinkoff_client(self):
        self.q_tokens

        # Смена токена
        token = self.q_tokens.popleft()
        self.q_tokens.append(token)

        return tinvest.SyncClient(token)


    def get_tinkoff_candles(self, figi, days=1):
        client = self.__get_tinkoff_client()

        curr_time = datetime.now()

        data = []
        
        if (date.today().weekday() - days) < 0:
            days += 3 # holidays + currient + days
        else:
            days += 1 # currient + days

        for day in range(days):
            try:
                data += client.get_market_candles(
                    figi=figi,
                    from_=curr_time - timedelta(days=day+1),
                    to=curr_time - timedelta(days=day),
                    interval=tinvest.CandleResolution.min5
                    ).dict()['payload']['candles']
            except Exception as e:
                self.logger.exception(e)
                raise Exception('--> tinkoff api - history - Ошибка загрузки исторических данных.')


        candles = pd.DataFrame.from_dict(data)
        candles = candles.rename(columns={'o': 'open', 'h': 'high',
                                        'l': 'low', 'c': 'close'})

        candles = candles[['time', 'open', 'high', 'low', 'close']]
        
        candles['time'] = candles['time'].dt.tz_convert('Europe/Moscow')
        candles.set_index('time', inplace=True)

        for col in ['open', 'high', 'low', 'close']:
            candles[col] = candles[col].astype(float, copy=False)
    
        return candles


    def __convert_to_unix(self, dt):
        unix_time = (dt - datetime(1970, 1, 1)).total_seconds()
        unix_time = int(unix_time)
        return unix_time

    
    def get_yahoo_candles(self, ticket, days=1):
        days += 3 # поправка на выходные

        curr_time = datetime.now()

        to = self.__convert_to_unix(curr_time)
        from_ = self.__convert_to_unix(curr_time - timedelta(days=days))       

        q = ('https://query1.finance.yahoo.com/v8/finance/chart/{0}'
            '?period1={1}&period2={2}&interval={3}&includePrePost=true'
            ).format(ticket, from_, to, '5m')

        try:
            with httpx.Client() as client:
                response = client.get(q)
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> yahoo api - history - Ошибка загрузки исторических данных.')
            
        data = response.json()["chart"]["result"][0]
        
        timestamps = data["timestamp"]
        
        ohlc = data["indicators"]["quote"][0]
        # volumes = ohlc["volume"]
        opens = ohlc["open"]
        highs = ohlc["high"]
        lows = ohlc["low"]
        closes = ohlc["close"]

        candles = pd.DataFrame({"open": opens,
                               "high": highs,
                               "low": lows,
                               "close": closes})

        candles.index = pd.to_datetime(timestamps, unit="s")
        
        candles.sort_index(inplace=True)
        candles.dropna(how='all', inplace=True)
        candles.drop_duplicates(inplace=True)
        candles = candles.groupby(candles.index).last()
        
        candles.index = candles.index.tz_localize("UTC").tz_convert(data["meta"]["exchangeTimezoneName"])
        candles.index.name = "time"

        return candles[:-1] # округляем до 5 минут


    def __get_tinkoff_last_price(self, figi):
        client = self.__get_tinkoff_client()

        try:
            price = client.get_market_orderbook(figi=figi, depth=1)
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> tinkoff api - last price - Ошибка загрузки последней цены.')

        price = price.dict()['payload']['last_price']

        return float(price)


    def __get_yahoo_last_price(self, ticker):
        q = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price'

        try:
            with httpx.Client() as client:
                response = client.get(q)
        except Exception as e:
            self.logger.exception(e)
            raise Exception('--> yahoo api - last price - Ошибка загрузки последней цены.')

        data = response.json()['quoteSummary']['result'][0]['price']

        # PREPRE, PRE, POSTPOST, POST, REGULAR
        try:
            if data['marketState'] == 'PRE':
                price = data['preMarketPrice']['raw']

            elif data['marketState'] == 'POST':
                price = data['postMarketPrice']['raw']

            else:
                price = data['regularMarketPrice']['raw']
            
            self.df_yahoo.loc[self.df_yahoo['ticker'] == ticker, 'last_price'] = price
        except:
            price = self.df_yahoo.loc[self.df_yahoo['ticker'] == ticker, 'last_price'].values[0]
            if price == -1:
                price = data['regularMarketPrice']['raw']

        return price


    def get_last_price(self):
        last_price = 0
        
        for _, row in self.df.iterrows():
            last_price += self.__get_tinkoff_last_price(row['figi']) * row['portion']


        ## Не стоит добавлять данные из yahoo api, хоть мне и не удалось спарсить
        ## пару компаний с тиньковского api, но это лишь не большая погрешность.
        ## А вот данные по ним из yahoo api лишь вносят шум.
        ## Включать на свой страх и риск.
        # for _, row in self.df_yahoo.iterrows():
        #     last_price += self.__get_yahoo_last_price(row['ticker']) * row['portion']

        last_price = last_price / 100

        return last_price