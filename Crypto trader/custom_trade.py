# Lets you place an order for a coin and it will auto sell based on stoploss which climbs with price
# DO NOT USE THIS
import sqlalchemy
from binance import Client
import pandas as pd
pd.options.mode.chained_assignment = None
import asyncio
import math
import time
import ta



async def buy_order(client, coinpair, buy_amount, current_price):
    """Create and send buy order"""
    if current_price >= buy_amount:
        buy_amount = round(buy_amount / current_price,2)
    else:
        buy_amount = math.floor(math.floor(buy_amount) / current_price)
    return client.create_order(symbol = coinpair,
                                    side = 'BUY',
                                    type = 'MARKET',
                                    quantity = buy_amount)


async def sell_order(client, coinpair, sell_amount):
    """Create and send sell order based on amount of USDT in wallet"""
    coin = coinpair[:-4]
    return client.create_order(symbol = coinpair,
                                    side = 'SELL',
                                    type = 'MARKET',
                                    quantity = sell_amount)
    
def write_to_log(coinpair, trade_db, order, stoploss=None):
    """Write buy and sell orders to logs"""
    if order['side'] == "BUY":
        order['fills'][0]['side'] = 'BUY'
    else:
        order['fills'][0]['side'] = 'SELL'
    order['fills'][0]['transactTime'] = order['transactTime']
    order['fills'][0]['stoploss'] = stoploss
    order = pd.DataFrame([order['fills'][0]])
    order.to_sql(coinpair+"_trade", trade_db, if_exists='append', index=False)

    
async def coin_info(trade_db, coin_db, client, exchange_info):
    while True:
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
        try:    
            trade_df = pd.read_sql("{}_trade".format(coin), trade_db)     
            if trade_df.side.iloc[-1] == "BUY":
                already_in = True
                buying_order = trade_df.iloc[-1]
                qty = float(buying_order.qty)
                stoploss = float(buying_order.stoploss)
                waiting = True
            else:
                already_in = False
        except:
            already_in = False

        if already_in == False:
            amount = input("How much of {} would you like to buy (USDT)".format(coin))
            stoploss = float(input("Starting stoploss for this trade?"))
            df = pd.read_sql(coin, coin_db)
            current_price = df.Price.iloc[-1]
            buying_order = await buy_order(client, coin, float(amount), float(current_price))
            buying_order['fills'][0]['qty'] = buying_order['executedQty']
            write_to_log(coin, trade_db, buying_order, stoploss)
            trade_df = pd.read_sql("{}_trade".format(coin), trade_db)   
            buying_order = trade_df.iloc[-1]
            qty = float(buying_order['qty'])
            waiting = True
        while True:
            time.sleep(1)
            df = pd.read_sql(coin, coin_db)
            post_buy_df = df[df.Time >= pd.to_datetime(buying_order['transactTime'], unit = 'ms')]
            if len(post_buy_df) != 0:
                if waiting == True:
                    post_buy_df['highest'] = post_buy_df.Price.cummax()
                    post_buy_df['climbingline'] = post_buy_df['highest'] * stoploss
                    if df.iloc[-1].Price >= float(buying_order['price']) * 1.0025:
                        post_buy_df['climbingstop'] = float(buying_order['price']) * 1.0019
                    else:
                        post_buy_df['climbingstop'] = post_buy_df.iloc[-1].climbingline
                if waiting == False:            
                    # check if rising
                    print("Rising, looking for exit")
                    post_buy_df['profitline'] = float(buying_order['price']) * 1.002
                    post_buy_df['highest'] = post_buy_df.Price.cummax()
                    post_buy_df['climbingline'] = post_buy_df['highest'] * 0.995
                    if post_buy_df.iloc[-1].climbingline > post_buy_df.iloc[-1].profitline:
                        post_buy_df['climbingstop'] = post_buy_df.iloc[-1].climbingline
                    else:
                        post_buy_df['climbingstop'] = post_buy_df.iloc[-1].profitline
                print("////////////\nBUY PRICE {} | CURRENT PRICE {:.10f} | STOP LOSS {:.10f}".format(buying_order['price'], post_buy_df.iloc[-1].Price, post_buy_df.iloc[-1].climbingstop))
                if post_buy_df.iloc[-1].Price <= post_buy_df.iloc[-1].climbingstop:
                    print(qty)
                    selling_order = await sell_order(client, coin, qty)
                    selling_order['fills'][0]['qty'] = selling_order['executedQty']
                    write_to_log(coin, trade_db, selling_order)
                    print(selling_order)
                    time.sleep(1)
                    break;
                elif df.iloc[-1].Price >= float(buying_order['price']) * 1.006:
                    waiting = False


trade_db = sqlalchemy.create_engine('sqlite:///Database/TRADECOINstream.db')
coin_db = sqlalchemy.create_engine('sqlite:///Database/COINUSDTstream.db')
keys = open('keys.txt', 'r')
api_key = keys.readline().strip()
secret_key = keys.readline().strip()
client = Client(api_key, secret_key)
exchange_info = client.get_exchange_info()

loop = asyncio.get_event_loop()
loop.run_until_complete(coin_info(trade_db, coin_db, client, exchange_info))
