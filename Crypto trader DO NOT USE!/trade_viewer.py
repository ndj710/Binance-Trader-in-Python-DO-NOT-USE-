# Looks at trades that have been made and then calculates and displays profit
import sqlalchemy
import pandas as pd
import time

trade_db = sqlalchemy.create_engine('sqlite:///Database/TRADECOINstream.db')

def get_trade_data(coin):
    df = pd.read_sql("{}USDT_trade".format(coin), trade_db)
    profit = 0
    if len(df) % 2 != 0:
        df = df[:-1]
    for i in range(0, len(df), 2):
        buyprice, sellprice = float(df.iloc[i].price), float(df.iloc[i+1].price)
        buyqty, sellqty = float(df.iloc[i].qty), float(df.iloc[i+1].qty)
        buycom, sellcom = buyprice * buyqty * 0.075 / 100, sellprice * sellqty * 0.075 / 100
        total_com = sellcom + buycom
        profit += (sellprice*sellqty - buyprice*buyqty) - total_com
    return profit




if __name__ == "__main__":
    coins = ["SHIB", "ADA", "MANA", "SOL", "DOGE", "SAND", "LRC", "GALA"]
    while True:
        profit = []
        for i in coins:
            try:
                profit.append(get_trade_data(i))
            except:
                pass
        print("Profit {:.10f}".format(sum(profit)))
        time.sleep(1)


        
        
        
