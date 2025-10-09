import openpyxl
from netmiko import ConnectHandler
import logging
from datetime import datetime

chemin_equipement = ""
chemin_configurations = ""


def set_chemin_excel(chemin):
    global chemin_equipement
    chemin_equipement = chemin
    print(f"[DEBUG] Chemin Excel défini dans configurations: {chemin_equipement}")


def set_chemin_config(chemin):
    global chemin_configurations
    chemin_configurations = chemin
    print(f"[DEBUG] Chemin config défini: {chemin_configurations}")


def lancer_configuration(username, password, scope="Y"):
    logs = []

    if not chemin_equipement:
        logs.append("❌ Aucun fichier Excel sélectionné.")
        return logs

    if not chemin_configurations:
        logs.append("❌ Aucun fichier de configuration sélectionné.")
        return logs

    # Activer les logs Netmiko pour debug
    logging.basicConfig(filename='netmiko_debug.log', level=logging.DEBUG)
    logger = logging.getLogger("netmiko")

    try:
        # Charger les commandes
        with open(chemin_configurations, "r") as file:
            config_commands = file.read().splitlines()
    except Exception as e:
        logs.append(f"❌ Erreur lors de la lecture du fichier de configuration : {str(e)}")
        return logs

    try:
        # Charger le fichier Excel
        workbook = openpyxl.load_workbook(chemin_equipement)
        sheet = workbook.active
    except Exception as e:
        logs.append(f"❌ Erreur lors de la lecture du fichier Excel : {str(e)}")
        return logs

    timestamp = datetime.now().strftime("%d.%m.%Y %H-%M")

    # Lecture des lignes Excel
    for row in sheet.iter_rows(min_row=4, values_only=True):
        hostname, ip, equipement_type, configurer = row

        if scope == "Y" and configurer != "Y":
            continue

        equipement = {
            "device_type": equipement_type,
            "host": ip,
            "username": username,
            "password": password,
            "secret": password,
            "timeout": 10,
            "global_delay_factor": 4,
            "session_log": "netmiko_log.txt",
        }

        try:
            connection = ConnectHandler(**equipement)
            logs.append(f"✅ Connexion réussie à {ip} ({connection.find_prompt()})")

            connection.enable()
            connection.send_config_set(config_commands)
            connection.save_config()

            vlan_output = connection.send_command("show vlan brief")
            logs.append(f"✅ Configuration appliquée à {ip}")
            logs.append(vlan_output)

            connection.disconnect()

        except Exception as e:
            logs.append(f"❌ Erreur avec l'équipement {ip} : {str(e)}")

    # Sauvegarder les logs
    log_filename = f"log_config ({timestamp}).txt"
    with open(log_filename, "w") as log_file:
        log_file.write("\n".join(logs))

    return logs