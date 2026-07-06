import time
import os
import requests
try:
    from requests_toolbelt.adapters.source import SourceAddressAdapter
except ImportError:
    SourceAddressAdapter = None
from logger_setup import logger
from camera import DDPAI
from network import NetworkManager
from shared import db, q_download, q_upload
from config import WIFI_DDPAI_SSID, WIFI_DDPAI_PASSWORD, WIFI_ASUS_SSID, WIFI_ASUS_PASSWORD

def network_controller() -> None:
    """
    Ağ bağlantılarını tarar ve duruma göre araç kamerası (DDPAI) 
    veya yerel ağa (ASUS) bağlanmayı dener.
    """
    logger.info("Network Controller başlatıldı.")
    NetworkManager.enable_wifi()
    
    while True:
        NetworkManager.start_scan()
        scanned_ssids = NetworkManager.get_scan_results()
        logger.info(f"Taranan SSID'ler: {scanned_ssids}")
        
        ddpai_ssid = next((s for s in scanned_ssids if WIFI_DDPAI_SSID in s), None)
        asus_ssid = next((s for s in scanned_ssids if WIFI_ASUS_SSID in s), None)
        connected_wifi = NetworkManager.get_connected_ssid()
        logger.info(f"Bağlı WiFi: {connected_wifi}")
        
        if ddpai_ssid:
            if connected_wifi != ddpai_ssid:
                logger.info("DDPAI ağına bağlı değil, şimdi bağlanılacak.")
                NetworkManager.connect_wifi(WIFI_DDPAI_SSID, WIFI_DDPAI_PASSWORD, "wpa2")
            else:
                logger.info("DDPAI kamerasına zaten bağlı.")
        elif asus_ssid:
            if connected_wifi != asus_ssid:
                logger.info("ASUS ağına bağlı değil, şimdi bağlanılacak.")
                NetworkManager.connect_wifi(WIFI_ASUS_SSID, WIFI_ASUS_PASSWORD, "wpa2")
            else:
                logger.info("ASUS ağına zaten bağlı.")
                
        logger.info("Ağ kontrolleri tamamlandı, 30 saniye dinleniliyor.")
        time.sleep(30)


def video_downloader_worker() -> None:
    """
    Araç kamerasına bağlantı sağlandığında cihazdaki video listesini kontrol eder 
    ve eksik olan dosyaları indirip kuyruğa ekler.
    """
    logger.info("Video Downloader Worker başlatıldı.")
    while True:
        connected_wifi = NetworkManager.get_connected_ssid()
        if connected_wifi and WIFI_DDPAI_SSID in connected_wifi:
            wifi_ip = NetworkManager.get_wifi_ip()
            if wifi_ip:
                camera = DDPAI(source_ip=wifi_ip)
                if camera.check_connection():
                    logger.info("Araç kamerası (DDPAI) bağlantısı aktif, video listesi alınıyor.")
                    camera.process_files()  # q_download kuyruğuna videoları ekler
                    
                    # Kuyruktaki dosyaları indir
                    while not q_download.empty():
                        filename = q_download.get()
                        logger.info(f"Video indiriliyor: {filename}")
                        local_path = camera.download_file(filename)
                        if local_path:
                            db.update_download(filename, local_path)
                            q_upload.put(filename)
                        q_download.task_done()
                        
                        # Eğer bağlantı koparsa indirme döngüsünden çık
                        current_wifi = NetworkManager.get_connected_ssid()
                        if not current_wifi or WIFI_DDPAI_SSID not in current_wifi:
                            logger.info("Video indirme esnasında DDPAI bağlantısı koptu.")
                            break
            else:
                logger.warning("DDPAI'ye bağlı görünüyor ancak wlan0 IP'si alınamadı.")
        time.sleep(30)


def gpx_downloader_worker() -> None:
    """
    Araç kamerasına bağlıyken GPX veya GPS konum verilerini indirip kaydeder.
    """
    logger.info("GPX Downloader Worker başlatıldı.")
    while True:
        connected_wifi = NetworkManager.get_connected_ssid()
        if connected_wifi and WIFI_DDPAI_SSID in connected_wifi:
            wifi_ip = NetworkManager.get_wifi_ip()
            if wifi_ip:
                camera = DDPAI(source_ip=wifi_ip)
                if camera.check_connection():
                    logger.info("Araç kamerası (DDPAI) üzerinden GPX verileri indiriliyor.")
                    camera.download_gpx()
        time.sleep(30)


def mobile_uploader_worker() -> None:
    """
    Mobil veri aktif ise kuyruktaki dosyaları sunucuya yükler veya simüle eder.
    """
    logger.info("Mobile Uploader Worker başlatıldı.")
    while True:
        mobile_ip = NetworkManager.get_mobile_data_ip()
        if mobile_ip:
            logger.debug(f"Mobil veri aktif, IP: {mobile_ip}. Yükleme işlemleri kontrol ediliyor.")
            
            # TODO: İskelet yükleme kodunuzu buraya ekleyebilirsiniz.
            # Örnek kullanım:
            # session = requests.Session()
            # if SourceAddressAdapter:
            #     adapter = SourceAddressAdapter(mobile_ip)
            #     session.mount('http://', adapter)
            #     session.mount('https://', adapter)
            
            # Şimdilik kuyruk üzerinden dosya silinerek yüklendiği simüle edilecek. Buraya ekleyeceğiniz yükleme fonksiyonu veya Objesi yükleme işlemini bitirip bu worker döngüsünden çıkınız.
            if not q_upload.empty():
                filename = q_upload.get()
                record = db.check_exists(filename)
                if record and record['file_path'] and os.path.exists(record['file_path']):
                    logger.info(f"Mobil veri üzerinden yükleniyor (simüle): {filename}")
                    
                    # Veritabanında yüklemenin başladığını işaretle
                    db.set_upload_start(filename)
                    
                    time.sleep(2)  # Yükleme simülasyonu
                    
                    # Yükleme bittiğinde URL ile birlikte veritabanını güncelle
                    dummy_url = f"https://bulut-depolama.net/yedek/{filename}"
                    db.set_upload_end(filename, dummy_url)
                    logger.info(f"Yükleme başarıyla tamamlandı: {dummy_url}")
                    
                    # try:
                    #     os.remove(record['file_path'])
                    # except Exception as e:
                    #     logger.error(f"Silme hatası: {e}")
                q_upload.task_done()
        time.sleep(30)


def wifi_uploader_worker() -> None:
    """
    Belirli bir WiFi ağına (ASUS) bağlıyken kuyruktaki dosyaları sunucuya yükler veya simüle eder.
    """
    logger.info("WiFi Uploader Worker başlatıldı.")
    while True:
        connected_wifi = NetworkManager.get_connected_ssid()
        if connected_wifi and WIFI_ASUS_SSID in connected_wifi:
            wifi_ip = NetworkManager.get_wifi_ip()
            if wifi_ip:
                logger.debug(f"ASUS WiFi aktif, IP: {wifi_ip}. Yükleme işlemleri kontrol ediliyor.")
                
                # TODO: İskelet yükleme kodunuzu buraya ekleyebilirsiniz.
                # Örnek kullanım:
                # session = requests.Session()
                # if SourceAddressAdapter:
                #     adapter = SourceAddressAdapter(wifi_ip)
                #     session.mount('http://', adapter)
                #     session.mount('https://', adapter)
                
                # Şimdilik kuyruk üzerinden dosya silinerek yüklendiği simüle edilecek. Buraya ekleyeceğiniz yükleme fonksiyonu veya Objesi yükleme işlemini bitirip bu worker döngüsünden çıkınız.
                if not q_upload.empty():
                    filename = q_upload.get()
                    record = db.check_exists(filename)
                    if record and record['file_path'] and os.path.exists(record['file_path']):
                        logger.info(f"WiFi (ASUS) üzerinden yükleniyor (simüle): {filename}")
                        
                        # Veritabanında yüklemenin başladığını işaretle
                        db.set_upload_start(filename)
                        
                        time.sleep(2)  # Yükleme simülasyonu
                        
                        # Yükleme bittiğinde URL ile birlikte veritabanını güncelle
                        dummy_url = f"https://bulut-depolama.net/yedek/{filename}"
                        db.set_upload_end(filename, dummy_url)
                        logger.info(f"Yükleme başarıyla tamamlandı: {dummy_url}")
                        
                        # try:
                        #     os.remove(record['file_path'])
                        # except Exception as e:
                        #     logger.error(f"Silme hatası: {e}")
                    q_upload.task_done()
            else:
                logger.warning("ASUS'a bağlı görünüyor ancak wlan0 IP'si alınamadı.")
        time.sleep(30)