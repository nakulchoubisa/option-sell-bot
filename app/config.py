# app/config.py
import os

BROKER = os.getenv("BROKER", "mock").lower()  # "mock" or "zerodha"

# Zerodha env
KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")
