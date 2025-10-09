import os
import pandas as pd
from netmiko import ConnectHandler
import getpass
from datetime import datetime

# Variables pour les chemins
chemin_equipement = ""
chemin_backup = ""


def set_chemin_excel(chemin):
    global chemin_equipement
    chemin_equipement = chemin


def set_chemin_backup(chemin):
    global chemin_backup
    chemin_backup = chemin


def lancer_backup_console():
    if not chemin_equipement:
        print("❌ Aucun fichier Excel sélectionné.")
        return

    try:
        equipements = pd.read_excel(chemin_equipement, header=2)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier Excel : {str(e)}")
        return

    if "Device Type" not in equipements.columns:
        print("❌ La colonne 'Device Type' n'existe pas dans le fichier Excel.")
        return

    equipements_cisco = equipements[equipements["Device Type"] == "cisco_ios"]
    if equipements_cisco.empty:
        print("❌ Aucun équipement de type 'cisco_ios' trouvé dans le fichier Excel.")
        return
    else:
        print(f"✅ {len(equipements_cisco)} équipement(s) Cisco IOS trouvé(s) dans le fichier Excel.")

    if not chemin_backup:
        print("❌ Aucun dossier de backup sélectionné.")
        return

    if not os.path.exists(chemin_backup):
        os.makedirs(chemin_backup)
        print(f"📂 Dossier 'backup/' créé à {chemin_backup}.")

    username = input("🔑 Entrez le nom d'utilisateur SSH : ")
    password = getpass.getpass("🔒 Entrez le mot de passe SSH : ")

    for _, row in equipements_cisco.iterrows():
        equipement_data = {
            "device_type": "cisco_ios",
            "host": row["IP Address"],
            "username": username,
            "password": password
        }

        try:
            print(f"⏳ Tentative de connexion à {row['Hostname']} ({row['IP Address']})...")
            connection = ConnectHandler(**equipement_data)
            print(f"✅ Connecté à {row['Hostname']} ({row['IP Address']})")

            timestamp = datetime.now().strftime("%d.%m.%Y %H.%M")
            config_backup = connection.send_command("show running-config")
            backup_filename = f"backup_{row['Hostname']}_{timestamp}.txt"
            backup_path = os.path.join(chemin_backup, backup_filename)

            with open(backup_path, "w") as backup_file:
                backup_file.write(config_backup)

            connection.disconnect()
            print(f"✅ Backup terminé pour {row['Hostname']}. Fichier enregistré : {backup_path}")

        except Exception as e:
            print(f"❌ Erreur lors de la connexion à {row['Hostname']} ({row['IP Address']}) : {e}")

    print("✅ Script terminé.")