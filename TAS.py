import wx
import wx.xrc
import wx.dataview
import threading
import time
import json
import datetime
import websocket
import _thread
import configparser

cf = configparser.ConfigParser()
cf.read("rich.ini")
key = cf.get("Key", "Public")
secret = cf.get("Key", "Secret")


class StockFrame(wx.Frame):
    OrderList = {}

    def __init__(self, stock1, stock2, parent):
        self.depth = None
        self.QuoteThread = None
        self.RefreshThread = None
        self.OrderThread = None
        self.Stock1 = stock1
        self.Stock2 = stock2
        self.StockText = stock1.upper() + "/" + stock2.upper()
        self.RequestStockText = stock1.lower() + stock2.lower()
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=wx.EmptyString, pos=wx.DefaultPosition,
                          size=wx.Size(293, 475), style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP | wx.TAB_TRAVERSAL)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
        self.SetFont(wx.Font(12, 70, 90, 90, False, "宋体"))

        gSizer8 = wx.GridSizer(0, 1, 0, 0)

        self.OrderView = wx.ListCtrl(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(280, 400), wx.LC_REPORT)
        self.OrderView.SetFont(wx.Font(10, 70, 90, 90, False, "宋体"))
        self.OrderView.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.OrderView.SetBackgroundColour(wx.Colour(64, 64, 64))

        gSizer8.Add(self.OrderView, 0, wx.ALL, 5)

        self.SetSizer(gSizer8)
        self.Layout()

        self.Centre(wx.BOTH)

    def DealOtherKey(self, key):
        return
        if key == wx.WXK_F4:
            if self.depth != None:
                self.BuyPrice.Value = str(self.depth["data"]["asks"][0])
                self.BuyQty.Value = str(self.DefaultBuy.Value)
                self.SetBuyEnable()
                self.SetSellDisable()
        elif key == wx.WXK_F3:
            if self.depth != None:
                self.SellPrice.Value = str(self.depth["data"]["bids"][0])
                self.SellQty.Value = str(self.DefaultSell.Value)
                self.SetSellEnable()
                self.SetBuyDisable()
        elif key == wx.WXK_F6:
            if self.depth != None:
                self.BuyPrice.Value = str(self.depth["data"]["bids"][0])
                self.BuyQty.Value = str(self.DefaultBuy.Value)
                self.SetBuyEnable()
                self.SetSellDisable()
        elif key == wx.WXK_F5:
            if self.depth != None:
                self.SellPrice.Value = str(self.depth["data"]["asks"][0])
                self.SellQty.Value = str(self.DefaultSell.Value)
                self.SetSellEnable()
                self.SetBuyDisable()
        elif key == wx.WXK_ESCAPE:
            self.CancelLast()
        elif key == wx.WXK_RETURN:
            if self.BuyButton.Enabled:
                self.DoBuy()
            elif self.SellButton.Enabled:
                self.DoSell()
        if key == wx.WXK_UP:
            if self.BuyButton.Enabled:
                box = self.BuyPrice
            elif self.SellButton.Enabled:
                box = self.SellPrice
            else:
                return
            Price = round(float(box.Value) + 0.0002, 6)
            box.Value = str(Price)
        elif key == wx.WXK_DOWN:
            if self.BuyButton.Enabled:
                box = self.BuyPrice
            elif self.SellButton.Enabled:
                box = self.SellPrice
            else:
                return
            Price = round(float(box.Value) - 0.0002, 6)
            box.Value = str(Price)
        if key == wx.WXK_RIGHT:
            if self.BuyButton.Enabled:
                box = self.BuyQty
            elif self.SellButton.Enabled:
                box = self.SellQty
            else:
                return
            Qty = float(box.Value)
            Qty += 100
            box.Value = str(Qty)
        elif key == wx.WXK_LEFT:
            if self.BuyButton.Enabled:
                box = self.BuyQty
            elif self.SellButton.Enabled:
                box = self.SellQty
            else:
                return
            Qty = float(box.Value)
            Qty -= 100
            box.Value = str(Qty)

    def MyFrame2OnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def QuoteListOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def OrderListOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def TickListOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def BuyPriceOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def SellPriceOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def BuyQtyOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def SellQtyOnKeyUp(self, event):
        self.DealOtherKey(event.KeyCode)
        event.Skip()

    def BuyButtonOnButtonClick(self, event):
        self.DoBuy()
        event.Skip()

    def SellButtonOnButtonClick(self, event):
        self.DoSell()
        event.Skip()

    def ButtonRefreshOnButtonClick(self, event):
        self.DoRefresh()

    def DoRefresh(self):
        return
        # Balance
        global api, Balances
        Result = api.get_balance()
        if Result != None and "data" in Result:
            for CurStock in Result["data"]:
                Balances[CurStock["currency"]] = [round(float(CurStock["balance"]), 4),
                                                  round(float(CurStock["available"]), 4)]
            self.ShowBalance()

        # Order
        TempList = {}
        OldList = self.OrderList.copy()
        partial_filled = api.list_orders(symbol="ftusdt", states="partial_filled")
        if partial_filled != None and partial_filled["status"] == 0:
            for CurOrder in partial_filled["data"]:
                self.OrderList[CurOrder["id"]] = CurOrder
                TempList[CurOrder["id"]] = CurOrder
        submitted = api.list_orders(symbol="ftusdt", states="submitted")
        if submitted != None and submitted["status"] == 0:
            for CurOrder in submitted["data"]:
                self.OrderList[CurOrder["id"]] = CurOrder
                TempList[CurOrder["id"]] = CurOrder
        for (key, CurOrder) in OldList.items():
            if key not in TempList:
                del self.OrderList[key]
        self.RefreshOrder(self.OrderList.copy())

    def SetBuyEnable(self):
        self.BuyButton.SetBackgroundColour(ButtonBuyColor)
        self.BuyButton.Enable(True)

    def SetBuyDisable(self):
        self.BuyButton.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.BuyButton.Enable(False)

    def SetSellEnable(self):
        self.SellButton.SetBackgroundColour(ButtonSellColor)
        self.SellButton.Enable(True)

    def SetSellDisable(self):
        self.SellButton.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.SellButton.Enable(False)

    def DoBuy(self):
        return
        global api
        # Result = api.buy(self.RequestStockText,  self.BuyPrice.Value, self.BuyQty.Value)
        if Result != None and Result["status"] == 0:
            print(Result)
        self.SetBuyDisable()
        print(Result)

    def DoSell(self):
        return
        global api
        # Result = api.sell(self.RequestStockText,  self.SellPrice.Value, self.SellQty.Value)
        if Result != None and Result["status"] == 0:
            print(Result)
        self.SetSellDisable()
        print(Result)

    def CancelOrder(self, id):
        return

    def CancelLast(self):
        return
        Orders = self.OrderList.copy()
        sorted(Orders, reverse=False)
        for (key, CurOrder) in Orders.items():
            self.CancelOrder(key)
            break;

    def SetItemText(self, CurOrder, ItemIndex):
        self.OrderView.SetItem(ItemIndex, 1, str(round(float(CurOrder["price"]), 6)))
        self.OrderView.SetItem(ItemIndex, 2, str(round(float(CurOrder["amount"]), 0)))
        self.OrderView.SetItem(ItemIndex, 3, str(round(float(CurOrder["filled_amount"]), 0)))

    def AddTAS(self, TAS):
        ItemIndex = self.OrderView.InsertItem(0, str(round(float(TAS["p"]), 5)));
        self.OrderView.SetItem(ItemIndex, 1, str(int(float(TAS["q"]))))
        self.OrderView.SetItem(ItemIndex, 2, datetime.datetime.fromtimestamp(int(TAS["T"])).strftime("%H:%M:%S"))
        pass

    def RefreshOrder(self, TempOrders):
        return
        DelList = {}
        for Index in range(0, self.OrderView.ItemCount):
            HadItem = False
            ItemData = self.OrderView.GetItemData(Index)
            for (key, CurOrder) in TempOrders.items():
                if CurOrder["created_at"] - BaseTimeT == ItemData:
                    HadItem = True;
                    break;
            if not HadItem:
                DelList[Index] = 0
        sorted(DelList, reverse=False)
        for CurIndex in DelList:
            self.OrderView.DeleteItem(CurIndex)
        for CurOrder in TempOrders.values():
            ItemIndex = -1
            OrderRealTime = CurOrder["created_at"]
            OrderTime = CurOrder["created_at"] - BaseTimeT
            for Index in range(0, self.OrderView.ItemCount):
                if self.OrderView.GetItemData(Index) == OrderTime:
                    ItemIndex = Index
                    break
            if ItemIndex >= 0:
                self.SetItemText(CurOrder, ItemIndex)
            else:
                ItemIndex = self.OrderView.InsertItem(0, datetime.datetime.fromtimestamp(OrderRealTime / 1000).strftime(
                    "%H:%M:%S"));
                self.OrderView.SetItemData(ItemIndex, OrderTime);
                t1 = self.OrderView.GetItem(ItemIndex);
                d1 = self.OrderView.GetItemData(ItemIndex);
                self.SetItemText(CurOrder, ItemIndex)

    def ShowBalance(self):
        global Balances
        if self.Stock1 in Balances:
            self.Stock1Balance.SetLabelText(str(Balances[self.Stock1][0]))
            self.Stock1CanUse.SetLabelText(str(Balances[self.Stock1][1]))
        if self.Stock2 in Balances:
            self.Stock2Balance.SetLabelText(str(Balances[self.Stock2][0]))
            self.Stock2CanUse.SetLabelText(str(Balances[self.Stock2][1]))

    def ShowQuote(self, quote):
        asks = quote["data"]["asks"]
        if len(asks) >= 20:
            Total = 0
            for i in range(10):
                self.QuoteList.SetItemText(9 - i, str(asks[i][0]));
                size = int(asks[i][1])
                Total += size
                self.QuoteList.SetItem(9 - i, 1, str(size));
                self.QuoteList.SetItem(9 - i, 2, str(Total));
        bids = quote["data"]["bids"]
        if len(bids) >= 20:
            Total = 0
            for i in range(10):
                self.QuoteList.SetItemText(11 + i, str(bids[i][0]));
                size = int(bids[i][1])
                Total += size
                self.QuoteList.SetItem(11 + i, 1, str(size));
                self.QuoteList.SetItem(11 + i, 2, str(Total));

    def FrameInit(self):
        self.SetTitle(self.StockText)

        self.OrderView.InsertColumn(0, "价格")
        self.OrderView.SetColumnWidth(1, 70)
        self.OrderView.InsertColumn(1, "数量")
        self.OrderView.SetColumnWidth(1, 60)
        self.OrderView.InsertColumn(2, "时间")
        self.OrderView.SetColumnWidth(2, 80)

    def __del__(self):
        pass


class RichCoreClass():
    def __init__(self, pw, key='', secret='', ):
        self.ParentWindow = pw
        self.key = key
        self.secret = secret
        self.DepthWs = None
        self.TickWs = None

    def on_TasMessage(self, ws, message):
        data = json.loads(message)
        self.ParentWindow.AddTAS(data)

    def on_DepthMessage(self, ws, message):
        data = json.loads(message)
        self.ParentWindow.ShowQuote(data)

    def on_DepthError(self, ws, error=None):
        print("Depth error:" + str(error), end="\n")

    def on_DepthClose(self, ws):
        print("Depth closed:" + str(ws), end="\n")
        self.SubDepth()

    def on_DepthOpen(self, ws):
        print("Depth open:" + str(ws), end="\n")

    def on_TickError(self, ws, error=None):
        ws.close()
        print("Tick error:" + str(error), end="\n")

    def on_TickClose(self, ws):
        print("Tick closed:" + str(ws), end="\n")
        self.SubTick()

    def TcikPing(self, ws):
        while True:
            b = bytearray(1)
            time.sleep(5)
            ws.send(b)

    def on_TickOpen(self, ws):
        # _thread.start_new_thread(self.TcikPing,(ws,))
        print("Tick open:" + str(ws), end="\n")

    def SubTick(self):
        if self.TickWs != None:
            self.TickWs.close()
            self.TickWs = None
        websocket.enableTrace(False)

        # self.TickWs = websocket.WebSocketApp("wss://www.richcore.com/stream?streams=tqceth@ticker/ethbtc@ticker",
        self.TickWs = websocket.WebSocketApp("wss://www.richcore.com/wires/RICHTUSDT/trades",
                                             on_message=self.on_TasMessage,
                                             on_error=self.on_TickError,
                                             on_close=self.on_TickClose)

        self.TickWs.on_open = self.on_TickOpen
        print("try to Open Tick", end="\n")
        self.TickWs.run_forever()

    def SubDepth(self):
        if self.DepthWs != None:
            self.DepthWs.close()
            self.DepthWs = None
        websocket.enableTrace(False)
        self.DepthWs = websocket.WebSocketApp("wss://www.richcore.com/stream?streams=richtusdt@depth",
                                              on_message=self.on_DepthMessage,
                                              on_error=self.on_DepthError,
                                              on_close=self.on_DepthClose)

        self.DepthWs.on_open = self.on_DepthOpen
        print("try to Open Depth", end="\n")
        self.DepthWs.run_forever()

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


if __name__ == "__main__":
    Balances = {}
    ButtonBuyColor = wx.Colour(6, 176, 124)
    ButtonSellColor = wx.Colour(255, 83, 83)
    BaseTimeT = int(time.time() * 1000)
    app = wx.App()
    CurStockFame = StockFrame("richc", "usdt", None)

    Rich = RichCoreClass(CurStockFame, key, secret)
    CurStockFame.Show()
    CurStockFame.FrameInit()
    # _thread.start_new_thread(Rich.SubDepth,())
    _thread.start_new_thread(Rich.SubTick, ())
    app.MainLoop()