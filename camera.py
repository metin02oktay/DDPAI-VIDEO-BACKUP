import requests
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from requests.adapters import HTTPAdapter
from tqdm import tqdm
try:
    from requests_toolbelt.adapters.source import SourceAddressAdapter
except ImportError:
    SourceAddressAdapter = None
from logger_setup import logger
from config import DOWNLOAD_DIR
from shared import db, q_download

class DDPAI:
    def __init__(self, ip: str = "193.168.0.1", source_ip: Optional[str] = None) -> None:
        self.base_url = f"http://{ip}"
        self.session = requests.Session()
        if source_ip and SourceAddressAdapter:
            adapter = SourceAddressAdapter(source_ip)
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
            logger.debug(f"DDPAI session bound to source IP: {source_ip}")
        else:
            if not SourceAddressAdapter and source_ip:
                logger.warning("requests-toolbelt not installed, ignoring source_ip")
            self.session.mount('http://', HTTPAdapter(pool_connections=10, pool_maxsize=10))

    def check_connection(self) -> bool:
        """Kamera ile olan HTTP bağlantısının durumunu kontrol eder."""
        try:
            return self.session.get(self.base_url, timeout=3).status_code == 200
        except:
            return False

    def process_files(self) -> bool:
        """Kamera hafızasındaki ön ve arka kameraların video dosyalarını indirme listesine ekler."""
        self.download_front_camera()
        self.download_back_camera()
        return True

    def download_front_camera(self) -> None:
        """Ön kameradaki video listesini çeker ve kuyruğa ekler."""
        try:
            url = f"{self.base_url}/vcam/cmd.cgi"
            resp = self.session.get(url, params={'cmd': 'APP_PlaybackListReq'}, timeout=10)
            data = json.loads(resp.text)
            
            if 'data' in data:
                inner_data = json.loads(data['data']) if isinstance(data['data'], str) else data['data']
                if 'file' in inner_data:
                    for f in inner_data['file']:
                        name = f.get('name')
                        record = db.check_exists(name)
                        if not record:
                            db.init_record(name)
                            q_download.put(name)
                        elif record and not record['is_download']:
                            q_download.put(name)
        except Exception as e:
            logger.error(f"Ön kamera hatası: {e}")

    def download_back_camera(self) -> None:
        """Arka kameradaki video listesini çeker ve kuyruğa ekler."""
        try:
            url = f"{self.base_url}/vcam/cmd.cgi"
            resp = self.session.get(url, params={'cmd': 'APP_PlaybackListReq_RearCam'}, timeout=10)
            data = json.loads(resp.text)
            
            if 'data' in data:
                inner_data = json.loads(data['data']) if isinstance(data['data'], str) else data['data']
                if 'file' in inner_data:
                    for f in inner_data['file']:
                        name = f.get('name')
                        record = db.check_exists(name)
                        if not record:
                            db.init_record(name)
                            q_download.put(name)
                        elif record and not record['is_download']:
                            q_download.put(name)
        except Exception as e:
            logger.error(f"Arka kamera hatası: {e}")
    
    def download_gpx(self) -> None:
        """GPX formatındaki GPS konum verilerini indirir, çözümler ve veritabanına kaydeder."""
        try:
            url = f"{self.base_url}/vcam/cmd.cgi"
            resp = self.session.get(url, params={'cmd': 'API_GpsFileListReq'}, timeout=10)
            data = json.loads(resp.text)
            if 'data' in data:
                inner_data = json.loads(data['data']) if isinstance(data['data'], str) else data['data']
                if 'file' in inner_data:
                    for f in inner_data['file']:
                        name = f.get('name')
                        if True:
                            file_url = f"{self.base_url}/{name}"
                            gpx_raw = ""
                            with self.session.get(file_url, stream=True, timeout=30) as r:
                                r.raise_for_status()
                                total_size = int(r.headers.get('content-length', 0))
                                with tqdm(desc=name, total=total_size, unit='iB', unit_scale=True, unit_divisor=1024) as bar:
                                    for chunk in r.iter_content(chunk_size=8192):
                                        if chunk:
                                            gpx_raw += chunk.decode('utf-8', errors='ignore')
                                            bar.update(len(chunk))
                            gpx_data_list = self.gpx_parse(gpx_raw)
                            db.insert_gpx(name, gpx_data_list)
        except Exception as e:
            logger.error(f"GPX indirme hatası: {e}")

    def gpx_parse(self, veri_metni: str) -> List[Dict[str, Any]]:
        """GPRMC ve GPGGA formatlarındaki NMEA/GPX verilerini parse eder."""
        sonuclar: Dict[str, Dict[str, Any]] = {}
        satirlar = veri_metni.strip().split('\n')
        for satir in satirlar:
            parcalar = satir.split(',')
            if satir.startswith('$GPRMC') and len(parcalar) >= 10:
                saat_anahtar = parcalar[1]
                if saat_anahtar not in sonuclar:
                    sonuclar[saat_anahtar] = {}
                saat_ham = parcalar[1].split('.')[0]
                tarih_ham = parcalar[9]
                zaman_str = f"{tarih_ham} {saat_ham}"
                zaman_obj = datetime.strptime(zaman_str, "%d%m%y %H%M%S")
                sonuclar[saat_anahtar].update({
                    "zaman": zaman_obj.strftime("%Y.%m.%d %H:%M:%S"),
                    "durum": parcalar[2],
                    "enlem": parcalar[3] + " " + parcalar[4] if parcalar[3] else None,
                    "boylam": parcalar[5] + " " + parcalar[6] if parcalar[5] else None,
                    "hiz_knot": round(float(parcalar[7]), 2) if parcalar[7] else None,
                    "hiz_kmh": round(float(parcalar[7]) * 1.852, 2) if parcalar[7] else None,
                    "yon_derece": round(float(parcalar[8]), 2) if parcalar[8] else None
                })
            elif satir.startswith('$GPGGA') and len(parcalar) >= 10:
                saat_anahtar = parcalar[1]
                if saat_anahtar not in sonuclar:
                    sonuclar[saat_anahtar] = {}
                sonuclar[saat_anahtar].update({
                    "enlem": parcalar[2] + " " + parcalar[3] if parcalar[2] else sonuclar[saat_anahtar].get("enlem"),
                    "boylam": parcalar[4] + " " + parcalar[5] if parcalar[4] else sonuclar[saat_anahtar].get("boylam"),
                    "uydu_sayisi": int(parcalar[7]) if parcalar[7] else None,
                    "rakim_metre": round(float(parcalar[9]), 2) if parcalar[9] else None
                })
        return list(sonuclar.values())

    def download_file(self, filename: str) -> Optional[str]:
        """Belirtilen isimdeki dosyayı kameradan indirir."""
        url = f"{self.base_url}/{filename}"
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        try:
            with self.session.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(local_path, 'wb') as f, tqdm(
                    desc=filename,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
            return local_path
        except Exception as e:
            logger.error(f"Dosya indirme hatası ({filename}): {e}")
            return None