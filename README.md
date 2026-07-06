# 🚗 Araç Kamerası Telefonla Yedekleme Sistemi (DDPAI Backup)

Bu proje tamamen hobi amaçlı kendi şahsi araç kameram olan DDPAI_Z60Pro için geliştirilmiş bir yedekleme otomasyonudur. Android cihaz üzerinde (root erişimi gerektirir) çalışarak DDPAI marka araç kamerasındaki video kayıtlarını (ön/arka) ve GPS/GPX verilerini otomatik olarak yedekler. 🤖📱

Sistem, Android cihazın Wi-Fi ve mobil ağ bağlantılarını sürekli izler, uygun koşullar oluştuğunda araç kamerasına bağlanarak yeni videoları çeker, ardından internet bağlantısı olan bir ağa (ev Wi-Fi ağı veya mobil veri) geçtiğinde bu dosyaları güvenle uzak bir sunucuya yükler. ☁️

## ✨ Özellikler

- 🌐 **Otomatik Ağ Yönetimi:** Ortamdaki Wi-Fi ağlarını (SSID) tarayarak uygun ağa akıllıca geçiş yapar (Araç kamerası veya ev ağı).
- ⬇️ **Otomatik İndirme:** Araç kamerasına (DDPAI) bağlanıldığında yeni ön/arka kamera kayıtlarını ve GPX verilerini yerel hafızaya anında indirir.
- ⬆️ **Otomatik Bulut Yedekleme (Cloud Backup):** İnternet erişimi (ASUS Wi-Fi ağı veya Mobil Veri) sağlandığında indirilen video dosyaları uzak bulut depolama sunucusuna yüklenerek güvenle yedeklenir.
- 📊 **Web Arayüzü:** İndirilen videoların listesini ve durumunu görüntüleyebileceğiniz, Flask tabanlı basit ve kullanıcı dostu bir yerel web paneli sunar. (Port: `8080`)
- 💾 **Veritabanı Takibi:** İndirme durumları, bulut yükleme başlangıç/bitiş süreçleri ve videoların buluttaki doğrudan URL (direkt link) adresleri dâhil tüm aşamalar SQLite (`veritabani.db`) üzerinden detaylı takip edilir.

## 🛠️ Gereksinimler

- 📱 Root erişimine sahip bir Android cihaz (veya benzeri root tabanlı Linux/Android ortamı).
- 🐍 Python 3.x
- ⚡ `uv` paket yöneticisi (Önerilen modern paket yöneticisi).

### 📱 Termux Üzerinde Kurulum (Android)

Android cihazınızda projeyi çalıştırmak için [Termux](https://termux.dev/) kullanabilirsiniz. Termux'u kurduktan sonra aşağıdaki adımları izleyin:

1. **Termux'u güncelleyin ve gerekli paketleri kurun:**
   ```bash
   pkg update && pkg upgrade -y
   pkg install python git -y
   ```

2. **Modern paket yöneticisi `uv`'yi kurun:**
   ```bash
   pip install uv
   ```

3. **Projeyi indirin ve bağımlılıkları yükleyin:**
   ```bash
   git clone <proje-repo-linki>
   cd telefonla-yedekle
   uv sync
   ```

4. **Ayarları Yapılandırın:** `config.example.json` dosyasının adını `config.json` olarak değiştirin ve içerisindeki ağ bilgilerini (SSID ve Şifre) kendi ağınıza göre düzenleyin. ⚙️
   ```json
   {
       "WIFI_DDPAI_SSID": "DDPAI_Z60Pro_D1C9",
       "WIFI_DDPAI_PASSWORD": "Sifre",
       "WIFI_ASUS_SSID": "ASUS",
       "WIFI_ASUS_PASSWORD": "Sifre"
   }
   ```

5. **Uygulamayı Başlatın:** Yine `uv` yardımıyla projeyi sanal ortam içerisinde kolayca çalıştırın:
   ```bash
   uv run main.py
   ```
   *(Uygulama arka planda `su` komutunu kullandığından, cihazınızın root yönetim uygulaması -örneğin Magisk- Termux için root izni isteyecektir. İzin vermeyi unutmayın)*

6. **Panele Erişin:** Telefonunuzun veya aynı ağdaki bilgisayarınızın tarayıcısından `http://<telefon_ip_adresi>:8080` adresine giderek web arayüzüne erişebilirsiniz. 🌍

## 🏗️ Mimari Yapı

Proje, eşzamanlı çalışan **5 farklı arkaplan işçisinden (worker)** oluşmaktadır:
1. 📡 **Network Controller:** Sürekli ağları tarar ve duruma göre kamera veya ev ağına bağlanır.
2. 🎥 **Video Downloader:** Kameraya bağlanıldığında video kayıtlarını tespit edip cihaz hafızasına (`downloads/` dizini) indirir.
3. 📍 **GPX Downloader:** GPX ve konum dosyalarını cihazdan çeker ve SQLite tablosuna (`gpx`) satır satır işler.
4. 📶 **Mobile Uploader:** Mobil veri aktif olduğunda, indirilen video dosyalarını bulut depolamaya yükleyerek veritabanına videonun doğrudan URL kaydını ekler.
5. 🏠 **WiFi Uploader:** Ev ağına (ASUS) bağlıyken, indirilen video dosyalarını bulut depolamaya yükleyerek veritabanına videonun doğrudan URL kaydını ekler.

> ⚠️ **Not:** Root ayrıcalıkları; `su`, `cmd wifi`, `svc wifi` ve `ip addr` gibi doğrudan Android OS shell komutlarını kullanabilmek için zorunludur.
