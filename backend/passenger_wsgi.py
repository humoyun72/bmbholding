"""
cPanel Python Selector — Passenger WSGI entry point

cPanel da sozlash:
  Application root:    /home/username/integritybot/
  Application URL:     yourdomain.com/api     (yoki api.yourdomain.com)
  Application startup file: passenger_wsgi.py
  Application Entry point:  application
  Python version:      3.12

Paketlarni o'rnatish (cPanel → Python Selector → pip):
  pip install -r requirements.txt
  pip install a2wsgi

.env fayl: /home/username/integritybot/.env  (barcha sozlamalar)
"""
import sys
import os

# Ilova papkasini Python path ga qo'shish
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# .env faylni yuklash
from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, ".env"))

# ASGI (FastAPI) → WSGI adapter (Passenger uchun)
from a2wsgi import ASGIMiddleware
from app.main import app as asgi_app

# Passenger bu o'zgaruvchini qidiradi
application = ASGIMiddleware(asgi_app, workers=1)
