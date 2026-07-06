import os
import json

DB_NAME = "veritabani.db"
DOWNLOAD_DIR = "downloads"

# config.json dosyasından ayarları yükle
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        _config_data = json.load(f)
except FileNotFoundError:
    _config_data = {}

# WiFi Configurations
WIFI_DDPAI_SSID = _config_data.get("WIFI_DDPAI_SSID", "")
WIFI_DDPAI_PASSWORD = _config_data.get("WIFI_DDPAI_PASSWORD", "")
WIFI_ASUS_SSID = _config_data.get("WIFI_ASUS_SSID", "")
WIFI_ASUS_PASSWORD = _config_data.get("WIFI_ASUS_PASSWORD", "")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)