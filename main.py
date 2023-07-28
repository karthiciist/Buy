import json
import math
import requests
from fyers_api import accessToken, fyersModel
from flask import Flask, render_template, request, redirect, send_file, url_for
from flask import Flask
from flask import request
import webbrowser
import yfinance as yf
from ta.trend import ADXIndicator
import datetime
import pandas as pd
import time
import numpy as np
import yfinance as yf
# from stockstats import StockDataFrame
import pyodbc
import http.client
import configparser

app = Flask(__name__)

redirect_url = "http://127.0.0.1:8097/process_authcode_from_fyers"
response_t = "code"
state = "sample_state"

config_obj = configparser.ConfigParser()
config_obj.read(".\configfile.ini")
dbparam = config_obj["mssql"]

server = dbparam["Server"]
db = dbparam["db"]

# To get client_id and client_secret from user and pass to fyers api
@app.route("/getauthcode", methods=['POST'])
def getauthcode():
    global client_id
    client_id = request.form.get('client_id')
    global client_secret
    client_secret = request.form.get('client_secret')
    session = accessToken.SessionModel(
        client_id=client_id,
        secret_key=client_secret,
        redirect_uri=redirect_url,
        response_type=response_t
    )

    response = session.generate_authcode()
    webbrowser.open(response)
    return response


# Fyres api will call back this methid with auth code. This method will use that auth code to generate access token
@app.route("/process_authcode_from_fyers")
def process_authcode_from_fyers():
    try:
        authcode = request.args.get('auth_code')
        session = accessToken.SessionModel(
            client_id=client_id,
            secret_key=client_secret,
            redirect_uri=redirect_url,
            response_type=response_t,
            grant_type="authorization_code"
        )
        session.set_token(authcode)
        response = session.generate_token()
        global access_token
        access_token = response["access_token"]
        print("access token ", access_token)
        global refresh_token
        refresh_token = response["refresh_token"]
        return render_template('authorized.html')
    except Exception as e:
        return {"status": "Failed", "data": str(e)}



@app.route("/run_buy", methods=['POST'])
def run_buy():
    while (True):
        try:
            time.sleep(10)
            conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};'
                                  r'Server=' + server + ';'
                                  'Database=' + db + ';'
                                  'Trusted_Connection=yes;')  # integrated security

            cursor = conn.cursor()

            SQLCommand = "SELECT * FROM [OCSTrade].[dbo].[OCS_Buy]"
            cursor.execute(SQLCommand)
            buy_line_items = cursor.fetchall()

            symbol = buy_line_items[0][0]
            buying_price = buy_line_items[0][1]
            stoploss = buy_line_items[0][2]
            hammer_high = buy_line_items[0][3]
            hammer_low = buy_line_items[0][4]
            timestamp = buy_line_items[0][5]
            epoch = buy_line_items[0][6]

            print(symbol, buying_price, stoploss, hammer_high, hammer_low, timestamp, epoch)








            # Connect broker to send buy order
            # data = {
            #     "symbol": symbol,
            #     "qty": 1,
            #     "type": 1,
            #     "side": 1,
            #     "productType": "INTRADAY",
            #     "limitPrice": 0,
            #     "stopPrice": 0,
            #     "validity": "DAY",
            #     "disclosedQty": 0,
            #     "offlineOrder": "False",
            #     "stopLoss": 0,
            #     "takeProfit": 0
            # }
            #
            # fyersModel.FyersModel.place_order(data)









            # insert into bought table
            conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};'
                                  r'Server=' + server + ';'
                                  'Database=' + db + ';'
                                  'Trusted_Connection=yes;')  # integrated security
            cur = conn.cursor()



            buying_price = float(hammer_high) + 2
            stoploss = float(hammer_low) - 1

            SQLCommand = (
                "INSERT INTO [OCSTrade].[dbo].[OCS_Bought] (orderid, symbol, bought_price, stoploss, timestamp) VALUES (?,?,?,?,?);")
            Values = ["", symbol, buying_price, stoploss, timestamp]

            cur.execute(SQLCommand, Values)

            conn.commit()
            print("Bought table successfully populated")
            conn.close()




            # Telegram notification
            # telegram_msg = "Buy signal for " + symbolparam["pesymbol"] + " generated"
            telegram_msg ="Buy order placed for " + str(symbol) + "%0A Order ID - " + "%0A Bought price - " + str(buying_price) + "%0A Stoploss - " + str(stoploss) + "%0A Time - " + str(timestamp)
            telegram_response = send_to_telegram(telegram_msg)
            print ("telegram_response -", telegram_response)






            # delete from buy table
            conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};'
                                  r'Server=' + server + ';'
                                  'Database=' + db + ';'
                                  'Trusted_Connection=yes;')  # integrated security
            cur = conn.cursor()

            SQLCommand = ("Delete from [OCSTrade].[dbo].[OCS_Buy]")

            cur.execute(SQLCommand)

            conn.commit()
            print("Buy table successfully cleared")
            conn.close()



        except Exception as e:
            print("Buy table empty")
            continue




def send_to_telegram(text):
    try:
        conn = http.client.HTTPSConnection("api.telegram.org")
        payload = ''
        headers = {}
        text = text.replace(" ", "%20")
        conn.request("POST", "/bot6386426510:AAHfwLLcNx9yOyqw2IKFxNFqJht4PCT49XA/sendMessage?chat_id=-876428015&text=" + text, payload, headers)
        res = conn.getresponse()
        data = res.read()
        # print(data.decode("utf-8"))
        return "Y"
    except Exception as e:
        print(e)
        return "N"





# @cross_origin("*")
@app.route('/gui')
def gui():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8097", debug=False)