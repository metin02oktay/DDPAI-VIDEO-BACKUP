import subprocess
import time
from typing import Optional, List
from logger_setup import logger

class RootShell:
    def __init__(self) -> None:
        self.process = subprocess.Popen(
            ["su"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.delimiter = "---END_OF_COMMAND---"

    def run(self, command: str) -> str:
        """Belirtilen komutu root shell üzerinde çalıştırır ve çıktısını döner."""
        if not self.process.stdin or not self.process.stdout:
            return ""
        
        self.process.stdin.write(f"{command}\n")
        self.process.stdin.write(f"echo {self.delimiter}\n")
        self.process.stdin.flush()
        
        output: List[str] = []
        while True:
            line = self.process.stdout.readline()
            if not line or self.delimiter in line:
                break
            output.append(line.strip())
        
        return "\n".join(output)

    def close(self) -> None:
        """Root shell işlemini sonlandırır."""
        if self.process.stdin:
            self.process.stdin.write("exit\n")
            self.process.stdin.flush()
        self.process.terminate()

class NetworkManager:
    _shell: Optional[RootShell] = None

    @classmethod
    def _get_shell(cls) -> RootShell:
        """Root shell örneğini döndürür, yoksa oluşturur."""
        if cls._shell is None:
            cls._shell = RootShell()
        return cls._shell

    @staticmethod
    def run_su_cmd(command: str) -> str:
        """Belirtilen komutu root ayrıcalıklarıyla çalıştırır."""
        try:
            shell = NetworkManager._get_shell()
            return shell.run(command)
        except Exception as e:
            logger.error(f"SU komut hatası: {e}")
            return ""

    @staticmethod
    def enable_wifi() -> None:
        """WiFi ve mobil veri bağlantılarını etkinleştirir."""
        NetworkManager.run_su_cmd('svc wifi enable')
        logger.info("WiFi başlatıldı")
        time.sleep(3)
        NetworkManager.run_su_cmd('svc data enable')
        logger.info("Veri bağlantısı başlatıldı")
        time.sleep(3)

    @staticmethod
    def start_scan() -> None:
        """WiFi ağlarını taramaya başlar."""
        NetworkManager.run_su_cmd('cmd wifi start-scan')
        logger.info("Tarama başlatıldı")
        time.sleep(5)

    @staticmethod
    def get_scan_results() -> List[str]:
        """Taranan WiFi ağlarının SSID listesini döner."""
        output = NetworkManager.run_su_cmd('cmd wifi list-scan-results')
        ssids = []
        for line in output.split('\n')[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                ssid_flags = parts[4:]
                ssid = ""
                for part in ssid_flags:
                    if part.startswith('['):
                        break
                    ssid += part + " "
                ssid = ssid.strip()
                if ssid:
                    ssids.append(ssid)
        return ssids

    @staticmethod
    def get_connected_ssid() -> Optional[str]:
        """Şu anda bağlı olunan WiFi ağının SSID bilgisini döner."""
        output = NetworkManager.run_su_cmd('cmd wifi status')
        if "Wifi is connected to" in output:
            for line in output.split('\n'):
                if line.strip().startswith("WifiInfo:"):
                    return line.split('WifiInfo:')[1].strip().split(',')[0].strip()
        return None

    @staticmethod
    def connect_wifi(ssid: str, password: str = "", security: str = "wpa2") -> bool:
        """Belirtilen SSID ve şifre ile WiFi ağına bağlanmaya çalışır."""
        NetworkManager.run_su_cmd(f'cmd wifi connect-network "{ssid}" {security} "{password}"')
        for _ in range(10):
            time.sleep(5)
            if NetworkManager.get_connected_ssid() == ssid:
                logger.info(f"{ssid} ağına bağlanıldı.")
                return True
        return False

    @staticmethod
    def get_interface_ip(interface_name: str) -> Optional[str]:
        """Belirtilen ağ arayüzünün IP adresini döner."""
        output = NetworkManager.run_su_cmd(f'ip -4 addr show {interface_name}')
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('inet '):
                # inet 192.168.0.100/24 brd 192.168.0.255 scope global wlan0
                parts = line.split()
                if len(parts) >= 2:
                    ip_with_subnet = parts[1]
                    ip = ip_with_subnet.split('/')[0]
                    return ip
        return None

    @staticmethod
    def get_wifi_ip() -> Optional[str]:
        """WiFi bağlantısının IP adresini döner."""
        return NetworkManager.get_interface_ip('wlan0')

    @staticmethod
    def get_mobile_data_ip() -> Optional[str]:
        """Mobil veri bağlantısının IP adresini döner."""
        output = NetworkManager.run_su_cmd('ip -4 addr')
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('inet '):
                parts = line.split()
                if len(parts) >= 2:
                    iface_name = parts[-1] # Genelde arayüz adı en sondadır
                    ip_with_subnet = parts[1]
                    ip = ip_with_subnet.split('/')[0]
                    
                    if 'wlan' not in iface_name and iface_name != 'lo' and 'dummy' not in iface_name and 'p2p' not in iface_name:
                        logger.debug(f"Mobil veri IP'si bulundu: {ip} (Arayüz: {iface_name})")
                        return ip
        return None

    @classmethod
    def cleanup(cls) -> None:
        """Ağ yöneticisi tarafından kullanılan kaynakları temizler."""
        if cls._shell:
            cls._shell.close()
            cls._shell = None