# This script was used for learning and will very likely lose money if used!
# DO NOT USE
import sqlalchemy
from binance import Client
import pandas as pd
pd.options.mode.chained_assignment = None
import asyncio
import ta
import math
import time
import matplotlib.pyplot as plt

# Key info
keys = open('keys.txt', 'r')
api_key = keys.readline().strip()
secret_key = keys.readline().strip()

# Get coin pair and check coin info
trade_db = sqlalchemy.create_engine('sqlite:///TRADECOINstream.db')
coin_db = sqlalchemy.create_engine('sqlite:///COINUSDTstream.db')
client = Client(api_key, secret_key)
exchange_info = client.get_exchange_info()
valid_coin = False
while not valid_coin:
    coin = input("Enter a valid coinpair in (USDT), for example 'SHIBUSDT' | ")
    for s in exchange_info['symbols']:
        if s['status'] == 'TRADING':
            if coin == s['symbol']:
                valid_coin = True
                print("COIN IS VALID PAIR")
    if valid_coin == False:
        print("Input coin pair is not valid")




# Trader object
class Binance_trade():
    def __init__(self, coin, client):
        '''initialise variables'''
        self.client = client
        self.coinpair = coin
        self.coin = coin[:-4]
        self.df = pd.DataFrame()
        self.open_position = False
        self.waiting = False


    def get_usdt(self):
        """Returns the current amount of USDT in wallet as a float"""
        assets = self.client.get_account()
        usdt = 0
        for i in range(len(assets['balances'])):
            if assets['balances'][i]['asset'] == 'USDT':
                usdt = assets['balances'][i]['free']
                break;   
        return float(usdt)
    
    
    def create_frame(self, data):
        """Create a dataframe to hold price information from the stream"""
        df = pd.DataFrame([data])
        df = df.loc[:, ['s', 'E', 'c']]
        df.columns = ['symbol', 'Time', 'Price']
        df.Price = df.Price.astype(float)
        df.Time = pd.to_datetime(df.Time, unit='ms')
        return df
    
    
    async def buy_order(self, current_price):
        """Create and send buy order"""
        buy_amount = math.floor(math.floor(self.get_usdt())
                                /float(current_price))
        return self.client.create_order(symbol = self.coinpair,
                                        side = 'BUY',
                                        type = 'MARKET',
                                        quantity = buy_amount)

    async def sell_order(self):
        """Create and send sell order based on amount of USDT in wallet"""
        assets = self.client.get_account()
        sell_amount = 0
        for i in range(len(assets['balances'])):
            if assets['balances'][i]['asset'] == self.coin:
                sell_amount = float(assets['balances'][i]['free'])
                break;
        return self.client.create_order(symbol = self.coinpair,
                                        side = 'SELL',
                                        type = 'MARKET',
                                        quantity = math.floor(sell_amount))
    
    
    def write_to_log(self, selling_order, buying_order):
        """Write buy and sell orders to logs"""
        buying_order['fills'][0]['side'] = 'BUY'
        selling_order['fills'][0]['side'] = 'SELL'
        buying_order['fills'][0]['qty'] = buying_order['executedQty']
        selling_order['fills'][0]['qty'] = selling_order['executedQty']
        
        buying_order = pd.DataFrame([buying_order['fills'][0]])
        selling_order = pd.DataFrame([selling_order['fills'][0]])
        buying_order.to_sql(self.coinpair+"_trade", trade_db, if_exists='append', index=False)
        selling_order.to_sql(self.coinpair+"_trade", trade_db, if_exists='append', index=False)
        #bs_orders = open('{}_trade_orders.txt'.format(self.coinpair), 'a')
        #line_to_write = '{} | {} | {}\n'.format(order['symbol'], order['fills'][0]['price'], order['fills'][0]['qty'])
        #bs_orders.write(line_to_write)
        #bs_orders.close()           
    
    
    async def coin_info(self):
        '''Print coin symbol, time and price'''

        self.df = pd.read_sql(self.coinpair, coin_db)
        self.df = self.df.iloc[-900:]
        self.df['EMA12'] = self.df.Price.ewm(span=12).mean()
        self.df['EMA26'] = self.df.Price.ewm(span=26).mean()
        self.df['MACD'] = self.df.EMA12 - self.df.EMA26
        self.df['signal'] = self.df.MACD.ewm(span=9).mean()
        #plt.plot(self.df.signal.iloc[-900:], label='signal', color='red')
        #plt.plot(self.df.MACD.iloc[-900:], label='MACD', color='green')
        #plt.legend()
        #plt.show()
        buy, sell = [], []
        for i in range(2, len(self.df), 60):
            if self.df.MACD.iloc[i] > self.df.signal.iloc[i] and self.df.MACD.iloc[i-60] < self.df.signal.iloc[i-60]:
                buy.append(i)
            elif self.df.MACD.iloc[i] < self.df.signal.iloc[i] and self.df.MACD.iloc[i-60] < self.df.signal.iloc[i-60]:
                sell.append(i)
        print(self.df.iloc[buy[0]].index)
        plt.scatter(self.df.iloc[buy].index, self.df.iloc[buy].Price, marker="^", color='green')
        plt.scatter(self.df.iloc[sell].index, self.df.iloc[sell].Price, marker="v", color='red')
        plt.plot(self.df.Price, label='COIN PRICE', color='k')
        plt.legend()
        plt.show()

my_trader = Binance_trade(coin, client)
loop = asyncio.get_event_loop()
loop.run_until_complete(my_trader.coin_info())
