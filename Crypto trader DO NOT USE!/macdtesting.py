# Testing different strats with some backtesting
# DO NOT USE
from binance import Client
import pandas as pd
import matplotlib.pyplot as plt
import ta
import sqlalchemy
from tqdm import tqdm
import math
import random
import numpy as np

coin_db = sqlalchemy.create_engine('sqlite:///Database/COINUSDTstream.db')
coins = ['SHIBUSDT', 'ADAUSDT', 'SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'MANAUSDT', 'SANDUSDT', 'CAKEUSDT', 'BNBUSDT', 'LRCUSDT', 'CKBUSDT']

keys = open('keys.txt', 'r')
api_key = keys.readline().strip()
secret_key = keys.readline().strip()

client = Client(api_key, secret_key)
def getpricedata(symbol):
    df = pd.DataFrame(client.get_historical_klines(symbol, '1m', '5d UTC'))
    df = df.iloc[:,:6]
    df.columns = ['Time','Open','High','Low','Close','Volume']
    df = df.set_index('Time')
    df.index = pd.to_datetime(df.index, unit='ms')
    df = df.astype(float)
    return df

def macd(df, a, b, c):
    df['EMA12'] = df.Price.ewm(span=a).mean()
    df['EMA26'] = df.Price.ewm(span=b).mean()
    df['MACD'] = df.EMA12 - df.EMA26
    df['signal'] = df.MACD.ewm(span=c).mean()
    
    buy, sell = [], []
    
    for i in range(2, len(df)):
        if df.MACD.iloc[i] > df.signal.iloc[i] and df.MACD.iloc[i-1] < df.signal.iloc[i-1]:
            buy.append(i)
        elif df.MACD.iloc[i] < df.signal.iloc[i] and df.MACD.iloc[i-1] > df.signal.iloc[i-1]:
            sell.append(i)    
    return (buy, sell)

def getplot(df, buy, sell):
    
    plt.scatter(df.iloc[buy].index, df.iloc[buy].Price, marker='^', color='green')
    plt.scatter(df.iloc[sell].index, df.iloc[sell].Price, marker='v', color='red')
    plt.plot(df.Price, label='COIN CLOSE', color='k')
    plt.legend()
    plt.show()


def getprofits(df, buy, sell):
    buyprices = df.Price.iloc[buy]
    sellprices = df.Price.iloc[sell]

    try:
        if sellprices.index[0] < buyprices.index[0]:
            sellprices = sellprices.drop(sellprices.index[0])
        if buyprices.index[-1] > sellprices.index[-1]:
            buyprices = buyprices.drop(buyprices.index[-1])
    except:
        pass
    profit = []
    for i in range(len(buyprices)):
        profit.append((sellprices[i] - buyprices[i]) / buyprices[i])
    try:    
        return(sum(profit) / len(profit) * 100)
    except:
        return"error div 0"

    
 
 
df = getpricedata("BTCUSDT")
df["%K"] = ta.momentum.stoch(df.High, df.Low, df.Close, window=14, smooth_window=3)
df["%D"] = df['%K'].rolling(3).mean()
df['rsi'] = ta.momentum.rsi(df.Close, window=14)
df['macd'] = ta.trend.macd_diff(df.Close)
df.dropna(inplace=True)

def gettriggers(df, lags, buy=True):
    dfx = pd.DataFrame()
    for i in range(1, lags+1):
        if buy:
            mask = (df['%K'].shift(i) < 20) & (df['%D'].shift(i) < 20)
        else:
            mask = (df['%K'].shift(i) > 80) & (df['%D'].shift(i) > 80)
        dfx = dfx.append(mask, ignore_index=True)
    return dfx.sum(axis=0)

print(np.where(gettriggers(df, 4,),1,0))
df['Buytrigger'] = np.where(gettriggers(df, 4,),1,0)
df['Selltriggers'] = np.where(gettriggers(df, 4, False),1,0)

df['Buy'] = np.where((df.Buytrigger) & (df['%K'].between(20,80)) & (df['%D'].between(20,80)) & (df.rsi > 50) & (df.macd > 0), 1, 0)
df['Sell'] = np.where((df.Selltriggers) & (df['%K'].between(20,80)) & (df['%D'].between(20,80)) & (df.rsi < 50) & (df.macd < 0), 1, 0)
print(df)

Buying_dates, Selling_dates = [], []
for i in range(len(df) - 1):
    if df.Buy.iloc[i]:
        Buying_dates.append(df.iloc[i + 1].name)
        for num, j in enumerate(df.Sell[i:]):
            if j:
                Selling_dates.append(df.iloc[i + num + 1].name)
                break


cutit = len(Buying_dates) - len(Selling_dates)
if cutit:
    Buying_dates = Buying_dates[:-cutit]

frame = pd.DataFrame({'Buying_dates':Buying_dates, 'Selling_dates':Selling_dates})
actuals = frame[frame.Buying_dates > frame.Selling_dates.shift(1)]
   
def profitcalc():
    Buyprices = df.loc[actuals.Buying_dates].Open
    Sellprices = df.loc[actuals.Selling_dates].Open
    return (Sellprices.values - Buyprices.values) / Buyprices.values
   

profits = profitcalc()
print(profits)
print(profits.mean())
plt.figure(figsize=(40,10))
plt.plot(df.Close, color='k', alpha=0.7)
plt.scatter(actuals.Buying_dates, df.Open[actuals.Buying_dates], marker="^", color='g', size=500)
plt.scatter(actuals.Selling_dates, df.Open[actuals.Selling_dates], marker="v", color='r', size=500)   
plt.legend()
plt.show()
        #a = 2.5
        #b = 3.3
        #c = 1.3
        #weights = [2.1, 3.6, 1.3]
        #lr = 0.01
        #bias = 1.8
        #count = 1
        #current_max = [-math.inf, a, b, c]
        #buy_best, sell_best = [], []
        #while count < 50:
            #a, b, c = a*weights[0], b*weights[1], c*weights[2]
            #count += 1
            #failed = False
            #buy, sell = macd(df, a, b, c)
            #current_stage = getprofits(df, buy, sell)
            #if current_stage == "error div 0":
                #failed = True
            #elif current_stage <= current_max[0]:
                #failed = True
            #elif current_stage > current_max[0]:
                #current_max = [current_stage, a, b, c]
                #buy_best = buy
                #sell_best = sell
            #if failed == True:
                #try:
                    #weights = [weights[i] * lr + bias for i in range(len(weights))]
                #except:
                    #print("Resetting")
                    #a, b, c = random.random(10), random.random(10), random.random(10)
                    #weights = [random.random(), random.random(), random.random()]

        #print(coin + ": ",current_max)
        #getplot(df, buy_best, sell_best)
    

