# Gets price of a coinpair and stores it in a database table
from binance import Client
import websockets
import json
import pandas as pd
import asyncio
import sqlalchemy
import time
engine = sqlalchemy.create_engine('sqlite:///Database/COINUSDTstream.db')

# Key info
keys = open('keys.txt', 'r')
api_key = keys.readline().strip()
secret_key = keys.readline().strip()

# Get coin pair and check coin info
client = Client(api_key, secret_key)
exchange_info = client.get_exchange_info()

valid_coin = False
while not valid_coin:
    coin = input("Enter a valid coinpair in (USDT) to get price of, for example 'SHIBUSDT': ")
    for s in exchange_info['symbols']:
        if s['status'] == 'TRADING':
            if coin == s['symbol']:
                valid_coin = True
                print("COIN IS VALID PAIR")
    if valid_coin == False:
        print("Input coin pair is not valid")


def create_frame(data):
    """Create a dataframe to hold price information from the stream"""
    df = pd.DataFrame([data])
    df = df.loc[:, ['s', 'E', 'c']]
    df.columns = ['symbol', 'Time', 'Price']
    df = df.set_index('Time')
    df.index = pd.to_datetime(df.index, unit='ms')
    df.Price = df.Price.astype(float)
    return df
        

async def coin_info(coin):
    '''Print coin symbol, time and price'''
    while True:
        try:
            stream = websockets.connect("wss://stream.binance.com:9443/stream?streams={}@miniTicker".format(coin.lower()))
            async with stream as receiver:
                while True:
                    data = await receiver.recv()
                    data = json.loads(data)['data']
                    frame = create_frame(data)
                    print(frame)
                    frame.to_sql(coin, engine, if_exists='append', index=True)
                    df = pd.read_sql(coin, engine)
        except:
            stream = None
            time.sleep(1)
            print("Reconnecting")



            
            
                

loop = asyncio.get_event_loop()
loop.run_until_complete(coin_info(coin))
