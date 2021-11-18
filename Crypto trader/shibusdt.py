# This script was used for learning and will very likely lose money if used!
# DO NOT USE
import websockets
import json
from binance import Client
import pandas as pd
import asyncio
import ta
import math


coin = 'SHIBUSDT'
stream = websockets.connect("wss://stream.binance.com:9443/stream?streams=shibusdt@miniTicker")

class Binance_trade():
    def __init__(self, stream, coin, api_key, secret_key):
        '''initialise variables'''
        self.api_key = api_key
        self.secret_key = secret_key
        self.client = Client(self.api_key, self.secret_key)
        self.stream = stream
        self.coin = coin
        self.df = pd.DataFrame()
        self.open_position = False
        self.waiting = False
        self.total_profit = 0
        self.starting_usdt = self.get_usdt()

    def get_usdt(self):
        """Returns the current amount of USDT in wallet as a float"""
        assets = self.get_account()
        usdt = 0
        for i in range(len(assets['balances'])):
            if assets['balances'][i]['asset'] == 'USDT':
                usdt = assets['balances'][i]['free']
                break;   
        return float(usdt)
            
            
    def get_account(self):
        '''Returns account info'''
        return self.client.get_account()
    
    
    def create_frame(self, data):
        """Create a dataframe to hold price information from the stream"""
        df = pd.DataFrame([data])
        df = df.loc[:, ['s', 'E', 'c']]
        df.columns = ['symbol', 'Time', 'Price']
        df.Price = df.Price.astype(float)
        df.Time = pd.to_datetime(df.Time, unit='ms')
        return df
    
    
    def buy_order(self, current_price):
        """Create and send buy order"""
        buy_amount = math.floor(math.floor(self.get_usdt())/float(current_price))
        return self.client.create_order(symbol = self.coin,
                                         side = 'BUY',
                                         type = 'MARKET',
                                         quantity = buy_amount)


    def sell_order(self):
        """Create and send sell order based on amount of USDT in wallet"""
        assets = self.get_account()
        sell_amount = 0
        for i in range(len(assets['balances'])):
            if assets['balances'][i]['asset'] == 'SHIB':
                sell_amount = float(assets['balances'][i]['free'])
                break;
        return self.client.create_order(symbol = self.coin,
                                         side = 'SELL',
                                         type = 'MARKET',
                                         quantity = math.floor(sell_amount))
    
    
    def write_to_log(self, bs, order):
        """Write buy and sell orders to logs"""
        bs_orders = open('{}_{}_orders.txt'.format(self.coin, bs), 'a')
        line_to_write = '{} | {} | {}\n'.format(order['symbol'], order['fills'][0]['price'], order['fills'][0]['qty'])
        bs_orders.write(line_to_write)
        bs_orders.close()           
    
    
    async def coin_info(self):
        '''Print coin symbol, time and price'''
        n = 1
        async with self.stream as receiver:
            while True:
                n += 1
                data = await receiver.recv()
                data = json.loads(data)['data']
                self.df = self.df.append(self.create_frame(data))
                buy_cond = []
                if len(self.df) >= 40:
                    # Checking momentum for 15 latest entries
                    for i in range(-1,-10,-1):
                        if i >= -7:
                            mask = ta.momentum.roc(self.df.Price, 30).iloc[i] >= 0
                        else:
                            mask = ta.momentum.roc(self.df.Price, 30).iloc[i] < 0
                        buy_cond.append(mask)
                    
                    if self.open_position == False:
                        print('BUYING | loop count: {} | Total profit {}'.format(n, self.total_profit))
                        print(sum(buy_cond) / len(buy_cond))
                        if sum(buy_cond) / len(buy_cond) == 1:
                            buying_order = self.buy_order(data['c'])
                            self.write_to_log('BUY', buying_order)
                            self.open_position = True
                    if self.open_position == True:
                        subdf = self.df[self.df.Time >= pd.to_datetime(buying_order['transactTime'], unit = 'ms')]
                        if len(subdf) != 0:
                            subdf['highest'] = subdf.Price.cummax()
                            subdf['trailingstop'] = subdf['highest'] * 0.995                            
                            if self.waiting == True:
                                # check if rising
                                print("Rising, looking for exit")
                                rising = []
                                for x in range(-1,-30,-1):
                                    mask = ta.momentum.roc(self.df.Price, 30).iloc[x] >= 0
                                    rising.append(mask)                                
                                print(sum(rising) / len(rising))
                                if subdf.iloc[-1].Price <= subdf.iloc[-1].trailingstop or sum(rising) / len(rising) < 0.55:
                                    selling_order = self.sell_order()
                                    current_usdt = self.get_usdt()
                                    self.total_profit = current_usdt - self.starting_usdt
                                    self.write_to_log('SELL', selling_order)
                                    self.open_position = False     
                                    self.waiting = False
                            
                            elif subdf.iloc[-1].Price <= subdf.iloc[-1].trailingstop:
                                selling_order = self.sell_order()
                                current_usdt = self.get_usdt()
                                self.total_profit = current_usdt - self.starting_usdt
                                self.write_to_log('SELL', selling_order)
                                self.open_position = False                            
                            elif self.df.iloc[-1].Price / float(buying_order['fills'][0]['price']) >= 1.0022:
                                self.waiting = True
                            print('SELLING | loop count: {} | Total profit {}'.format(n, self.total_profit))
                            print("Current price {:.10f} Sell at {:.10f} for profit or {:.10f} for a loss".format(subdf.iloc[-1].Price, 
                                                                                                        float(buying_order['fills'][0]['price'])*1.0022,
                                                                                                        subdf.iloc[-1].trailingstop))                              

    
# Key information
keys = open('keys.txt', 'r')

api_key = keys.readline().strip()
secret_key = keys.readline().strip()

my_trader = Binance_trade(stream, coin, api_key, secret_key)
loop = asyncio.get_event_loop()
loop.run_until_complete(my_trader.coin_info())