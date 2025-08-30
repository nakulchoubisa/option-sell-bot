# app/brokers/zerodha_data.py
from typing import Dict, Any
from kiteconnect import KiteConnect
import requests
import os
import io
import zipfile
import pandas as pd
class ZerodhaData:
    def __init__(self, api_key: str, access_token: str):
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

    def ltp(self, symbol: str) -> float:
        data = self.kite.ltp(symbol)
        return data[symbol]["last_price"]

    def instruments(self):
        """
        Fetch the full instruments list (options, futures, equity).
        Returns Pandas DataFrame
        """
        return pd.DataFrame(self.kite.instruments())

    def option_chain(self, underlying: str = "NIFTY"):
        """
        Filter only option contracts for given underlying
        """
        df = self.instruments()
        df = df[(df["segment"] == "NFO-OPT") & (df["name"] == underlying)]
        return df.to_dict(orient="records")
