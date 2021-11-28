# Just some testing stuff for MACD
# DO NOT USE THIS
from binance import Client
import pandas as pd
import ta


keys = open('keys.txt', 'r')

api_key = keys.readline().strip()
secret_key = keys.readline().strip()

client = Client(api_key, secret_key)

def getminutedata(symbol):
    df = pd.DataFrame(client.get_historical_klines(symbol, '1m', '60m UTC'))
    df = df.iloc[:,:6]
    df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = df.set_index('Time')
    df.index = pd.to_datetime(df.index, unit='ms')
    df = df.astype(float)
    return df


def tradingstrat(symbol, qty, open_position=False):
    while True:
        df = getminutedata(symbol)
        if not open_position:
            print("Looking for buy in")
            print(ta.trend.macd_diff(df.Close).iloc[-1])
            if ta.trend.macd_diff(df.Close).iloc[-1] > 0 and ta.trend.macd_diff(df.Close).iloc[-2] < 0:

                order = client.create_order(symbol = symbol,
                                            side = 'BUY',
                                            type = 'MARKET',
                                            quantity = qty)
                buyprice = float(order['fills'][0]['price'])
                open_position = True
        if open_position:
            print("Looking for sell out")
            if ta.trend.macd_diff(df.Close).iloc[-1] < 0 and ta.trend.macd_diff(df.Close).iloc[-2] > 0:
                order = client.create_order(symbol = symbol,
                                            side = 'SELL',
                                            type = 'MARKET',
                                            quantity = qty)
                sellprice = float(order['fills'][0]['price'])
                print(f'profit = {(sellprice - buyprice) / buyprice}')
                open_position = False
                
tradingstrat("SHIBUSDT", 400000)