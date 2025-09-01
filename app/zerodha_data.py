# app/brokers/zerodha_data.py
from typing import Dict, Any
import os
import requests
import pandas as pd
from kiteconnect import KiteConnect

class ZerodhaData:
    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    def ltp(self, symbol: str) -> float:
        try:
            data = self.kite.ltp(symbol)
            return data[symbol]["last_price"]
        except Exception as e:
            raise Exception(f"LTP fetch failed: {e}")

   # app/brokers/zerodha_data.py
from typing import Dict, Any
import os
import requests
import pandas as pd
from kiteconnect import KiteConnect

class ZerodhaData:
    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    def ltp(self, symbol: str) -> float:
        try:
            data = self.kite.ltp(symbol)
            return data[symbol]["last_price"]
        except Exception as e:
            raise Exception(f"LTP fetch failed: {e}")

   def sync_instruments(self):
        try:
            instruments = self.kite.instruments("NFO")  # or "NSE" for equities
            # store in DB or a file
            with open("instruments.json", "w") as f:
                import json
                json.dump(instruments, f)
            return len(instruments)
        except Exception as e:
            print("Error syncing instruments:", e)
            return 0

    def get_options(self, symbol: str) -> list:
        """
        Load option contracts for given symbol (e.g. NIFTY, BANKNIFTY).
        """
        try:
            csv_path = os.path.join(os.getcwd(), "data", "NFO_instruments.csv")
            if not os.path.exists(csv_path):
                raise Exception("Run sync_instruments first.")

            df = pd.read_csv(csv_path)

            # Filter only options for symbol
            options = df[
                (df["segment"] == "NFO-OPT") &
                (df["name"] == symbol)
            ][["instrument_token", "tradingsymbol", "expiry", "strike", "instrument_type"]]

            return options.to_dict(orient="records")
        except Exception as e:
            raise Exception(f"Option fetch failed: {e}")





    def get_options(self, symbol: str) -> list:
        """
        Load option contracts for given symbol (e.g. NIFTY, BANKNIFTY).
        """
        try:
            csv_path = os.path.join(os.getcwd(), "data", "NFO_instruments.csv")
            if not os.path.exists(csv_path):
                raise Exception("Run sync_instruments first.")

            df = pd.read_csv(csv_path)

            # Filter only options for symbol
            options = df[
                (df["segment"] == "NFO-OPT") &
                (df["name"] == symbol)
            ][["instrument_token", "tradingsymbol", "expiry", "strike", "instrument_type"]]

            return options.to_dict(orient="records")
        except Exception as e:
            raise Exception(f"Option fetch failed: {e}")




