import threading
from flask import Flask, render_template, jsonify, send_from_directory
from config import DOWNLOAD_DIR
from shared import db, q_download, q_upload
from workers import (
    network_controller,
    video_downloader_worker,
    gpx_downloader_worker,
    mobile_uploader_worker,
    wifi_uploader_worker
)

app = Flask(__name__)

@app.route('/')
def index():
    """Ana sayfayı oluşturur ve video verilerini gösterir."""
    videolar = db.get_all()
    return render_template('index.html', videolar=videolar)

@app.route('/api/data')
def api_data():
    """Video verilerini JSON formatında döner."""
    return jsonify(db.get_all())
    
@app.route('/api/status')
def api_status():
    """Kuyruktaki indirme ve yükleme işlemlerinin durumunu döner."""
    return jsonify({
        "q_download": q_download.qsize(),
        "q_upload": q_upload.qsize()
    })

@app.route('/video/<path:filename>')
def serve_video(filename: str):
    """İndirilen videoları istemciye sunar."""
    return send_from_directory(DOWNLOAD_DIR, filename)

if __name__ == "__main__":
    threading.Thread(target=network_controller, daemon=True).start()
    threading.Thread(target=video_downloader_worker, daemon=True).start()
    threading.Thread(target=gpx_downloader_worker, daemon=True).start()
    threading.Thread(target=mobile_uploader_worker, daemon=True).start()
    threading.Thread(target=wifi_uploader_worker, daemon=True).start()
    
    app.run(host='0.0.0.0', port=8080)