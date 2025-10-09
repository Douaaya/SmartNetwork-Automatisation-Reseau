import os
import paramiko
from datetime import datetime
import logging
from typing import Tuple, Dict, List
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
import pandas as pd

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SFTPManager:
    def __init__(self):
        self.connection = None
        self.host = None
        self.port = None
        self.username = None
        self.password = None
        self.remote_path = None

    def configure(self, host, port, username, password, remote_path):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.remote_path = remote_path

    def test_connection(self):
        try:
            import paramiko
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.username, password=self.password)
            transport.close()
            return True, "Connexion SFTP réussie"
        except Exception as e:
            return False, f"Échec connexion SFTP: {str(e)}"

    def upload_backup(self, local_file_path):
        """Upload un fichier vers le serveur SFTP"""
        try:
            import paramiko
            import os

            # Créer la connexion
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.username, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Vérifier/Créer le dossier distant
            remote_dir = os.path.join(self.remote_path, os.path.basename(os.path.dirname(local_file_path)))
            try:
                sftp.stat(remote_dir)
            except IOError:
                sftp.mkdir(remote_dir)

            # Upload du fichier
            remote_file_path = os.path.join(remote_dir, os.path.basename(local_file_path))
            sftp.put(local_file_path, remote_file_path)

            sftp.close()
            transport.close()

            return True, f"Fichier uploadé vers {remote_file_path}"
        except Exception as e:
            return False, f"Échec upload SFTP: {str(e)}"

class BackupManager:
    def __init__(self):
        self.sftp = SFTPManager()
        self.session_name = ""
        self.stop_flag = False

    def create_session_folder(self, base_path: str) -> str:
        """Crée un sous-dossier daté pour la session de backup"""
        self.session_name = datetime.now().strftime("backup_%Y-%m-%d_%H-%M-%S")
        session_path = os.path.join(base_path, self.session_name)
        os.makedirs(session_path, exist_ok=True)
        return session_path

    def backup_device(self, device: Dict[str, str], username: str, password: str, session_path: str) -> Tuple[
        bool, str]:
        """Sauvegarde un équipement avec messages détaillés"""
        hostname = device.get('Hostname', 'inconnu')
        ip = str(device.get('IP Address', '')).strip()

        if not ip or ip == '0.0.0.0':
            return False, f"❌ IP invalide pour {hostname}"

        try:
            # Connexion à l'équipement
            with ConnectHandler(
                    device_type='cisco_ios',
                    host=ip,
                    username=username,
                    password=password,
                    timeout=30
            ) as conn:
                # Récupération de la configuration
                config = conn.send_command("show running-config")

                # Sauvegarde locale
                filename = f"backup_{hostname}_{ip}.txt"
                local_path = os.path.join(session_path, filename)

                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(config)

                # Transfert SFTP
                sftp_status = ""
                if self.sftp.config['enabled']:
                    success, remote_path = self.sftp.upload_file(local_path, self.session_name)
                    sftp_status = f" | SFTP: {'✅ ' + remote_path if success else '❌ ' + remote_path}"

                return True, f"✅ {hostname} ({ip}) | Local: {local_path}{sftp_status}"

        except NetmikoTimeoutException:
            return False, f"❌ Timeout sur {ip}"
        except NetmikoAuthenticationException:
            return False, f"❌ Authentification échouée sur {ip}"
        except Exception as e:
            return False, f"❌ Erreur sur {ip}: {str(e)}"

    def backup_all_devices(self, excel_path: str, backup_dir: str, username: str, password: str) -> List[str]:
        """Lance la sauvegarde complète avec suivi en temps réel"""
        session_path = self.create_session_folder(backup_dir)
        results = []

        try:
            df = pd.read_excel(excel_path, header=2)
            devices = df[df["Device Type"] == "cisco_ios"].to_dict('records')

            for device in devices:
                if self.stop_flag:
                    results.append("🟠 Backup interrompu")
                    break

                status, message = self.backup_device(device, username, password, session_path)
                results.append(message)

            results.append(f"\n📊 Résultat: {len([r for r in results if '✅' in r])}/{len(devices)} succès")
            return results
        except Exception as e:
            return [f"❌ Erreur globale: {str(e)}"]


