# This script was used for learning and will very likely lose money if used!
# DO NOT USE
import sqlalchemy
from binance import Client
import pandas as pd
pd.options.mode.chained_assignment = None
import asyncio
import math
import time
import ta

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
    coin = input("Enter a valid coinpair in (USDT), for example 'SHIBUSDT': ")
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
       
    
    
    async def coin_info(self):
        '''Print coin symbol, time and price'''
        n = 1
        while True:
            time.sleep(1)
            n += 1
            self.df = pd.read_sql(self.coinpair, coin_db)
            self.df = self.df[-2000:]
            if len(self.df) < 2000:
                print("filling up dataframe {}/900".format(len(self.df)))
                print(self.df)
            if len(self.df) >= 2000:
                buy_cond = []
                for i in range(-1,-120,-1):
                    if i >= -80:
                        mask = ta.momentum.roc(self.df.Price, 120).iloc[i] >= 0
                    else:
                        mask = ta.momentum.roc(self.df.Price, 120).iloc[i] < 0
                    buy_cond.append(mask)
                if self.open_position == False:
                    print('{} | BUYING {} | Current price {:.10f}'.format(n, self.coin, self.df.iloc[-1].Price))
                    print("Current condition {:.5f}".format(sum(buy_cond) / len(buy_cond)))
                    print("Need positive {:.10f}\nNeed negative {:.10f}".format(ta.trend.macd_diff(self.df.Price).iloc[-60], ta.trend.macd_diff(self.df.Price).iloc[-120]))
                    if sum(buy_cond) / len(buy_cond) >= 0.9 and ta.trend.macd_diff(self.df.Price).iloc[-60] > 0 and ta.trend.macd_diff(self.df.Price).iloc[-120] < 0:
                        try:
                            buying_order = await self.buy_order(self.df.iloc[-1].Price)
                            self.open_position = True
                        except:
                            time.sleep(5)
                if self.open_position == True:
                    subdf = self.df[self.df.Time >= pd.to_datetime(buying_order['transactTime'], unit = 'ms')]
                    if len(subdf) != 0:
                        if self.waiting == False:
                            subdf['highest'] = subdf.Price.cummax()
                            subdf['trailingstop'] = subdf['highest'] * 0.999
                        if self.waiting == True:            
                            # check if rising
                            print("Rising, looking for exit")
                            subdf['highest'] = subdf.Price.cummax()
                            subdf['trailingstop'] = subdf['highest'] * 0.997
                            if subdf.iloc[-1].Price <= subdf.iloc[-1].trailingstop:
                                selling_order = await self.sell_order()
                                self.write_to_log(selling_order, buying_order)
                                self.open_position = False     
                                self.waiting = False
                                time.sleep(5)
                            
                        elif subdf.iloc[-1].Price <= subdf.iloc[-1].trailingstop:
                            selling_order = await self.sell_order()
                            self.write_to_log(selling_order, buying_order)
                            self.open_position = False
                            time.sleep(5)
                        if self.df.iloc[-1].Price >= float(buying_order['fills'][0]['price']) * 1.0024:
                            self.waiting = True
                        print('\n{} | SELLING {} |'.format(n, self.coin))
                        print("Buy price {:.10f}\nCurrent Price {:.10f}\nSell at {:.10f} or above for profit\nCurrent stoploss {:.10f}\n///////////////////////////////".format(float(buying_order['fills'][0]['price']),subdf.iloc[-1].Price, float(buying_order['fills'][0]['price'])*1.0024, subdf.iloc[-1].trailingstop))                              
  

my_trader = Binance_trade(coin, client)
loop = asyncio.get_event_loop()
loop.run_until_complete(my_trader.coin_info())
