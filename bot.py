import binance
import time
import pandas
from ta import trend
import math
from binance.helpers import round_step_size

# variables constantes
API_KEY = "" #clé api
API_SECRET = "" #clé secrette de l'api
# à changer pour passer à une autre crypto ou une autre paire
CRYPTO_SYMBOL = "BTC"
FIAT_SYMBOL = "USDC"
PAIR_SYMBOL = "BTCUSDC"
MY_TRUNCATE = 4 # ne pass toucher de préférence 

class Trading():
    def __init__(self):
        self.client = binance.Client(api_key=API_KEY, api_secret=API_SECRET)
        self.pairSymbol = PAIR_SYMBOL
        self.fiatSymbol = FIAT_SYMBOL
        self.cryptoSymbol = CRYPTO_SYMBOL

    def get_exchange_info(self): #récolte les données du marché
        data = self.client.get_historical_klines(symbol=self.pairSymbol, interval=self.client.KLINE_INTERVAL_3MINUTE, start_str=str(float(time.time() - (3600 * 24 * 30))), end_str=str(float(time.time())))
        #crée un tableau de valeurs pour mieux se repérer
        df = pandas.DataFrame(data=data, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "qa_volume", "no_trades", "tbb_asset_volume", "tbq_asset_volume", "ignore"])

        #supprime les colonnes inutiles
        del df["open_time"]
        del df["open"]
        del df["volume"]
        del df["close_time"]
        del df["qa_volume"]
        del df["no_trades"]
        del df["tbb_asset_volume"]
        del df["tbq_asset_volume"]
        del df["ignore"]

        #les moyennes
        df["SMA7"] = trend.sma_indicator(df["close"], 7)
        df["SMA25"] = trend.sma_indicator(df["close"], 25)

        return df

    def get_account_balance(self, coin): #récupère les données du compte (nombre de stable coin et crypto)
        jsonBalance = self.client.get_account()
        if jsonBalance == []:
            return 0

        pandaBalance = pandas.DataFrame(jsonBalance["balances"])
        pandaBalance.set_index(pandaBalance["asset"], inplace=True, drop=True)

        #cherche la monnaie passé en paramètre
        if not coin in pandaBalance["asset"].values:
            return 0
        else:
            return pandaBalance.loc[coin].iloc[-2]

    #troncature à 4 décimal donc 3 0 après la virgule
    def truncate(self, n, decimals = 0):
        trunc = 10 ** decimals
        r = float(math.floor(n * trunc) / trunc)
        return r

    def trade(self):
        #récupère le prix actuel ainsi que les fonds du compte courant
        actualPrice = float(self.get_exchange_info()["close"].iloc[-1])
        fiatAmount = float(self.get_account_balance(self.fiatSymbol))
        cryptoAmount = float(self.get_account_balance(self.cryptoSymbol))

        #affiche ces valeures
        print(actualPrice)
        print(fiatAmount)
        print(cryptoAmount)

        tick_size = '0.01'
        
        if self.get_exchange_info()["SMA7"].iloc[-2] < self.get_exchange_info()["SMA25"].iloc[-2]: #si courbe rose au dessus de la courbe jaune
            qtyToBuy = self.truncate(fiatAmount / actualPrice, MY_TRUNCATE)
            if qtyToBuy > 0.0001:
                limit = (actualPrice - ((actualPrice * 0.3) / 100))
                roundedToTick = round_step_size(limit, tick_size)
                print(f"Limite prix {roundedToTick}")
                self.client.create_order(symbol=self.pairSymbol, side=self.client.SIDE_BUY, type=self.client.ORDER_TYPE_LIMIT, timeInForce=self.client.TIME_IN_FORCE_GTC, quantity=qtyToBuy, price=roundedToTick)
            else:
                print("Pas assez de fond pour acheter la crypto")
        elif self.get_exchange_info()["SMA7"].iloc[-2] > self.get_exchange_info()["SMA25"].iloc[-2]: #si courbe jaune au dessus de la courbe rose
            qtyToSell = self.truncate(cryptoAmount, MY_TRUNCATE)
            if qtyToSell > 0.0001:
                limit = (actualPrice + ((actualPrice * 0.3) / 100))
                roundedToTick = round_step_size(limit, tick_size)
                print(f"Limite prix {roundedToTick}")
                self.client.create_order(symbol=self.pairSymbol, side=self.client.SIDE_SELL, type=self.client.ORDER_TYPE_LIMIT, timeInForce=self.client.TIME_IN_FORCE_GTC, quantity=qtyToSell, price=roundedToTick)
            else:
                print("Pas assez de crypto pour vendre")
        else: #dans le cas ou il n'y a rien à faire
            print("Rien à faire pour l'instant !") 

if __name__ == "__main__":
    trader = Trading()
    try:
        trader.trade()
    except binance.BinanceAPIException as e:
        print(e)
