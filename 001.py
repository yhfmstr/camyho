import numpy
import talib
from talib import MA_Type
import numpy as np
import smtplib
import csv

import krakenex

import decimal
import time
from datetime import datetime

pair = 'XXRPZEUR'
base_currency = 'ZEUR'
interval = 5
minimum = 30

k = krakenex.API()
k.load_key('kraken.key')

def now():
    return decimal.Decimal(time.time())

def lineprint(msg, targetlen = 72):
    line = '-'*5 + ' '
    line += str(msg)

    l = len(line)
    if l < targetlen:
        trail = ' ' + '-'*(targetlen-l-1)
        line += trail

    print(line)
    return

ohlc = k.query_public('OHLC',{'pair': pair, 'interval': interval})

while True:
    try:
        
        action = 'NULL'

        lineprint(datetime.fromtimestamp(now()))
        timestamp = datetime.fromtimestamp(now())

        balance = k.query_private('Balance')
        tradebalance = k.query_private('TradeBalance', data = {'asset': base_currency})
        tradebalance = tradebalance['result']['eb']

        #fees = k.query_private('TradeVolume', data = {'pair':pair})
       
        tradehistory = k.query_private('TradesHistory')
        balanceXXRP = balance['result']['XXRP']
        balanceZEUR = balance['result']['ZEUR']
        tradespair=[]
        for keys in tradehistory['result']['trades']:
            tradespair.append(tradehistory['result']['trades'][keys])
        
        lasttrade_time = tradespair[0]['time']
        lasttrade_type = tradespair[0]['type']
        lasttrade_price = tradespair[0]['price']
        lasttrade_amount = tradespair[0]['vol']

        #print(tradespair[0])

        print('balance XRP: ', balanceXXRP)
        print('balance EUR: ', balanceZEUR)
        print('Total (EUR): ', tradebalance)
        #print('Trade history: ', tradehistory)
     
        ret= []
        ret = k.query_public('OHLC', data = {'pair': pair, 'interval': interval})

        ohlc = ret['result'][pair]

        openprice = [x[1] for x in ohlc]
        highprice = [x[2] for x in ohlc]
        lowprice = [x[3] for x in ohlc]
        closeprice = [x[4] for x in ohlc]
        volumeprice = [x[6] for x in ohlc] 

        openprice = [float(x) for x in openprice]
        np_openprice = np.array(openprice)

        highprice = [float(x) for x in highprice]
        np_highprice = np.array(highprice)

        lowprice = [float(x) for x in lowprice]
        np_lowprice = np.array(lowprice)
        
        closeprice = [float(x) for x in closeprice]
        np_closeprice = np.array(closeprice)

        volumeprice = [float(x) for x in volumeprice]
        np_volumeprice = np.array(volumeprice)

        last_price = closeprice [-1:]
        
        RSI = talib.RSI(np_closeprice, timeperiod=14)
        MFI = talib.MFI(np_highprice, np_lowprice, np_closeprice, np_volumeprice, timeperiod = 14)
        MACD, MACDsignal, MACDhist = talib.MACD(np_closeprice, fastperiod=10, slowperiod=26, signalperiod=9)
        BBupper, BBmiddle, BBlower = talib.BBANDS(np_closeprice, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

        RSIf = RSI[-1:]
        MFIf = MFI[-1:]
        MACDf = MACD[-1:]
        MACDsignalf = MACDsignal [-1:]
        MACDhistf = MACDhist [-1:]

        print('Actual price :', last_price)
        
        print('RSI = ',RSIf)
        print('MFI = ',MFIf)
        #print('MACD = ',MACDf)
        #print('MACDsignal = ',MACDsignalf)
        print('MACDhist = ',MACDhistf)
        print('BB up :', BBupper[-1:])
        print('BB low :', BBlower[-1:])

        last_price = last_price[0]

        fee_sell = (0.0026*last_price)
        fee_buy = (0.0016*last_price)
        print('fees sell = ', fee_sell)
        print('fees buy = ', fee_buy)

        print('last trade type: ', lasttrade_type)
        print('last trade date: ', datetime.fromtimestamp(lasttrade_time))
        print('last trade price: ', lasttrade_price)

        if(lasttrade_type =='sell' and (float(lasttrade_price) < float(last_price+(0.001)))):
            print('BUYYY to cover at price of : ', (last_price+0.02))
        

        if(lasttrade_type =='buy' and (float(lasttrade_price) > float(last_price +(0.001)))): 
            print('SELL to cover at price of : ', (last_price+0.02))
         

        if ((lasttrade_time + 240) > now()):
            print('Too early to trade since last trade: we should do nothing')


        if ((lasttrade_time + 240) < now()):
            print('Time is OK, we can trade')            
            
            if(RSIf > 55 and last_price > (BBupper[-1:]*0.9975) and MACDhistf > 0.0008):
                print('SELL')
                action = 'SELL'
                s_price = last_price+(fee_sell/2)
                s_price = round(s_price, 5)
                n = now() + 240
                neworder = k.query_private('AddOrder',
                    {'pair': pair,
                     'type': 'sell',
                     'ordertype': 'limit',
                     'price': s_price,
                     'volume': minimum,
                     'expiretm': n,
                    })
              
                print(neworder)

            if(RSIf < 40 and last_price < BBlower[-1:]*1.0025 and MACDhistf < -0.0008):
                print('BUY')
                action = 'BUY'
                b_price = last_price-(fee_buy/2)
                b_price = round(b_price, 5)
                n = now + 240
                neworder = k.query_private('AddOrder',
                    {'pair': pair,
                     'type': 'buy',
                     'ordertype': 'limit',
                     'price': b_price,
                     'volume': minimum,
                     'starttm': 0,
                     'expiretm': n
                    })
              
                print(neworder)
                
            if(MACDhistf > 0.003): print('MACD greater than 0.003 -> sell?')
            if(MACDhistf < -0.003): print('MACD less than 0.003 -> buy?')

        lineprint('END')
    
        savingaction = open('XXRPZEUR_Action_001.csv', 'a')
        with savingaction:
            fieldnames = ['currency', 'timestamp', 'price', 'total balance', 'action', 'quantity' ]
            writer = csv.DictWriter(savingaction, fieldnames=fieldnames, lineterminator = '\n')
            writer.writerows([{'currency': 'XRPEUR', 'timestamp' : timestamp, 'price': last_price, 'total balance': tradebalance, 'action': action ,'quantity' : minimum}]) 

    except KeyError:
        pass

    time.sleep(30)



    print('hello')
