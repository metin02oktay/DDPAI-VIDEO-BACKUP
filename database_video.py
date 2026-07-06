import sqlite3
import threading
from typing import Optional, List, Dict, Any
from logger_setup import logger

class DatabaseManager:
    def __init__(self, db_name: str) -> None:
        self.db_name = db_name
        self.lock = threading.Lock()
        self.create_tables()

    def get_connection(self) -> sqlite3.Connection:
        """Yeni bir veritabanı bağlantısı oluşturur ve döner."""
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def create_tables(self) -> None:
        """Gerekli veritabanı tablolarını (videolar ve gpx) oluşturur."""
        with self.lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS videolar (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE,
                        file_path TEXT,
                        is_download BOOLEAN DEFAULT 0,
                        start_time INTEGER DEFAULT NULL,
                        end_time INTEGER DEFAULT NULL,
                        download_time INTEGER DEFAULT NULL,
                        is_gpx_add BOOLEAN DEFAULT 0,
                        is_upload BOOLEAN DEFAULT 0,
                        is_upload_start BOOLEAN DEFAULT 0,
                        is_upload_end BOOLEAN DEFAULT 0,
                        upload_url TEXT DEFAULT NULL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS gpx (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        start_time INTEGER DEFAULT NULL,
                        end_time INTEGER DEFAULT NULL,
                        download_time INTEGER DEFAULT NULL,
                        is_gpx_add BOOLEAN DEFAULT 0,
                        zaman TEXT DEFAULT NULL,
                        durum TEXT DEFAULT NULL,
                        enlem TEXT DEFAULT NULL,
                        boylam TEXT DEFAULT NULL,
                        hiz_knot TEXT DEFAULT NULL,
                        hiz_kmh TEXT DEFAULT NULL,
                        yon_derece TEXT DEFAULT NULL,
                        uydu_sayisi INTEGER DEFAULT NULL,
                        rakim_metre INTEGER DEFAULT NULL,
                        video_id INTEGER DEFAULT NULL
                    )
                ''')
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Tablo oluşturulurken hata: {e}")

    def check_exists(self, name: str) -> Optional[Dict[str, Any]]:
        """Belirtilen isme sahip kaydın veritabanında olup olmadığını kontrol eder."""
        with self.lock:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videolar WHERE name = ?", (name,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

    def init_record(self, name: str) -> None:
        """Veritabanına yeni bir dosya kaydı ekler."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO videolar (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()

    def update_download(self, name: str, file_path: str) -> None:
        """İndirme işleminin tamamlandığını kaydeder ve dosya yolunu günceller."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE videolar SET is_download = 1, file_path = ? WHERE name = ?", (file_path, name))
            conn.commit()
            conn.close()

    def update_upload(self, name: str) -> None:
        """Dosyanın yüklenme işleminin tamamlandığını kaydeder."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE videolar SET is_upload = 1 WHERE name = ?", (name,))
            conn.commit()
            conn.close()

    def set_upload_start(self, name: str) -> None:
        """Yükleme işleminin başladığını veritabanına kaydeder."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE videolar SET is_upload_start = 1 WHERE name = ?", (name,))
            conn.commit()
            conn.close()

    def set_upload_end(self, name: str, url: str) -> None:
        """Yükleme işleminin bittiğini ve dosyanın uzak sunucu adresini veritabanına kaydeder."""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE videolar 
                SET is_upload = 1, is_upload_end = 1, upload_url = ? 
                WHERE name = ?
            ''', (url, name))
            conn.commit()
            conn.close()
            
    def insert_gpx(self, name: str, gpx_data_list: List[Dict[str, Any]]) -> None:
        """Ayrıştırılmış GPX veya GPS konum verilerini veritabanına ekler."""
        if not gpx_data_list:
            return
            
        with self.lock:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM gpx WHERE name = ?", (name,))
                if cursor.fetchone()[0] > 0:
                    conn.close()
                    return

                for row in gpx_data_list:
                    cursor.execute('''
                        INSERT INTO gpx (
                            name, zaman, durum, enlem, boylam, hiz_knot, hiz_kmh, yon_derece, uydu_sayisi, rakim_metre
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        name, row.get('zaman'), row.get('durum'), row.get('enlem'), row.get('boylam'),
                        row.get('hiz_knot'), row.get('hiz_kmh'), row.get('yon_derece'), row.get('uydu_sayisi'), row.get('rakim_metre')
                    ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"GPX veritabanı hatası ({name}): {e}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Veritabanındaki tüm video kayıtlarını liste halinde döner."""
        with self.lock:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videolar ORDER BY id DESC")
            rows = [dict(ix) for ix in cursor.fetchall()]
            conn.close()
            return rows