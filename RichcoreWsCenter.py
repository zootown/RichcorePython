import hmac
import hashlib
import requests
import time
import base64
import websocket
import json
import threading
import socket
import sys
import _thread
import configparser

DepthWs = None
TasWs = None


def StartDepthWs(rich):
    DepthThread = DepthWsClass(rich)
    DepthThread.start()


def StartTASWs(rich):
    TASThread = TASWsClass(rich)
    TASThread.start()


class DepthWsClass(threading.Thread):
    def __init__(self, rich):
        threading.Thread.__init__(self)
        self.Rich = rich

    def run(self):
        global DepthWs
        if DepthWs != None:
            DepthWs.close()
            DepthWs = None
        websocket.enableTrace(False)
        DepthWs = websocket.WebSocketApp("wss://www.richcore.com/stream?streams=richtusdt@depth",
                                         on_message=self.Rich.on_DepthMessage,
                                         on_error=self.Rich.on_DepthError,
                                         on_close=self.Rich.on_DepthClose)

        DepthWs.on_open = self.Rich.on_DepthOpen
        print("try to Open Depth", end="\n")
        DepthWs.run_forever()


class TASWsClass(threading.Thread):
    def __init__(self, rich):
        threading.Thread.__init__(self)
        self.Rich = rich

    def run(self):
        global TasWs
        if TasWs != None:
            TasWs.close()
            TasWs = None
        websocket.enableTrace(False)

        #self.TickWs = websocket.WebSocketApp("wss://www.richcore.com/stream?streams=tqceth@ticker/ethbtc@ticker",
        TasWs = websocket.WebSocketApp("wss://www.richcore.com/wires/RICHTUSDT/trades",
                                       on_message=self.Rich.on_TasMessage,
                                       on_error=self.Rich.on_TasError,
                                       on_close=self.Rich.on_TasClose)

        TasWs.on_open = self.Rich.on_TasOpen
        print("try to TAS Tick", end="\n")
        TasWs.run_forever()


class RichCoreClass():
    def __init__(self, pw, key='', secret='', ):
        self.ParentWindow = pw
        self.key = key
        self.secret = secret

    def on_TasMessage(self, ws, message):
        TASClientLock.acquire()
        CientList = TASCientList.copy()
        TASClientLock.release()
        for CurClient in CientList:
            try:
                CurClient.send(message.encode())
            except socket.timeout:
                print("time out then close TASClient " + str(ws))
                CurClient.close()
                TASCientList.remove(CurClient)
            except Exception as error:
                print("SendDepthMessage error then close TASClient " + str(ws))
                CurClient.close()
                TASCientList.remove(CurClient)

    def on_DepthMessage(self, ws, message):
        DepthClientLock.acquire()
        CientList = DepthCientList.copy()
        DepthClientLock.release()
        for CurClient in CientList:
            try:
                CurClient.send(message.encode())
            except socket.timeout:
                print("time out then close DepthClient " + str(ws))
                CurClient.close()
                DepthCientList.remove(CurClient)
            except Exception as error:
                print("SendDepthMessage error then close DepthClient " + str(ws))
                CurClient.close()
                DepthCientList.remove(CurClient)

    def on_DepthError(self, ws, error=None):
        print("Depth error:" + str(error), end="\n")

    def on_DepthClose(self, ws):
        print("Depth closed:" + str(ws), end="\n")
        StartDepthWs(self)

    def on_DepthOpen(self, ws):
        print("Depth open:" + str(ws), end="\n")

    def on_TasError(self, ws, error=None):
        ws.close()
        print("TAS error:" + str(error), end="\n")

    def on_TasClose(self, ws):
        print("TAS closed:" + str(ws), end="\n")
        StartTASWs(self)

    def TasPing(self, ws):
        while True:
            b = bytearray(1)
            time.sleep(5)
            ws.send(b)

    def on_TasOpen(self, ws):
        # _thread.start_new_thread(self.TcikPing,(ws,))
        print("TAS open:" + str(ws), end="\n")

    def get_signed(self, outtime):
        # sig_str = base64.b64encode(sig_str.encode())
        # signature = base64.b64encode(hmac.new(self.secret.encode(), sig_str, digestmod=hashlib.sha1).digest())
        timestamp = str(int(time.time()))
        outtime.append(timestamp)
        signature = hmac.new(self.secret.encode(), timestamp.encode(), digestmod=hashlib.sha256).digest().hex().replace(
            "-", "").lower()
        return signature

    def sign_request(self, method, url, params):
        timestr = []
        sign = self.get_signed(timestr)
        headers = {
            'x-mbx-signature': sign,
            'x-mbx-timestamp': timestr[0],
            'x-mbx-apikey': key,
            'content-type': 'multipart/form-data'
        }

        try:
            r = requests.request(method, url, headers=headers, json=params)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
            print(r.text)
        if r.status_code == 200:
            return r.json()
        else:
            return str(r)

    def GetMarket(self):
        return self.sign_request("GET", "https://www.richcore.com/api/v1/markets")

    def GetMarketByCoin(self, coin):
        return self.sign_request("GET", "https://www.richcore.com/api/v1/markets/" + coin)

    def GetOrders(self):
        return self.sign_request("GET", "https://www.richcore.com/api/v1/agencies")

    def GetOrderByID(self, ID):
        return self.sign_request("GET", "https://www.richcore.com/api/v1/agencies/" + ID)

    def CancelOrder(self, ID):
        return self.sign_request("DELETE", "https://www.richcore.com/api/v1/agencies/" + ID)

    def GetWallets(self):
        return self.sign_request("GET", "https://www.richcore.com/api/v1/wallets")

    def GetWalletsByCoin(self, coin):
        return self.sign_request("GET", "https://www.richcore.com/api/v1/wallets/" + coin)

    def LimitBuy(self):
        paras = {
            # 'application/x-www-form-urlencoded': "agency%5Bmarket%5D=RICHCUSDT&agency%5Baim%5D=buy&agency%5Bprice%5D=0.011&agency%5Bamount%5D=100"
        }
        return self.sign_request("POST", "https://www.richcore.com/api/v1/agencies/limit", paras)

    def LimitSell(self):
        paras = {
            # 'application/x-www-form-urlencoded': "agency%5Bmarket%5D=RICHCUSDT&agency%5Baim%5D=sell&agency%5Bprice%5D=10&agency%5Bamount%5D=100",
        }
        return self.sign_request("POST", "https://www.richcore.com/api/v1/agencies/limit", paras)


cf = configparser.ConfigParser()
cf.read("rich.ini")
key = cf.get("Key", "Public")
secret = cf.get("Key", "Secret")

Rich = RichCoreClass(key, secret)
DepthCientList = set()
DepthClientLock = threading.Lock()
HadSubDepth = False
TASCientList = set()
TASClientLock = threading.Lock()
HadSubTAS = False


class DepthThreadClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global HadSubDepth, DepthClientLock, DepthCientList, Rich
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 9999
        serversocket.bind(('127.0.0.1', port))
        # 设置最大连接数，超过后排队
        serversocket.listen(5)
        print("建立Depth服务", end='\n')

        while True:
            clientsocket, addr = serversocket.accept()
            print("Depth请求连入: %s" % str(addr), end='\n')
            DepthClientLock.acquire()
            clientsocket.settimeout(5)
            DepthCientList.add(clientsocket)
            DepthClientLock.release()

            if not HadSubDepth:
                StartDepthWs(Rich)
                HadSubDepth = True


class TASThreadClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global HadSubTAS, TASClientLock, TASCientList, Rich
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 9998
        serversocket.bind(('127.0.0.1', port))
        # 设置最大连接数，超过后排队
        serversocket.listen(5)
        print("建立TAS服务", end='\n')

        while True:
            clientsocket, addr = serversocket.accept()
            print("TAS请求连入: %s" % str(addr), end='\n')
            TASClientLock.acquire()
            TASCientList.add(clientsocket)
            TASClientLock.release()

            if not HadSubTAS:
                StartTASWs(Rich)
                HadSubTAS = True


if __name__ == '__main__':
    DepthThread = DepthThreadClass()
    DepthThread.start()
    TASThread = TASThreadClass()
    TASThread.start()




