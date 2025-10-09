import openpyxl
from netmiko import ConnectHandler
import logging
from datetime import datetime

chemin_equipement = ""


def set_chemin_excel(chemin):
    global chemin_equipement
    chemin_equipement = chemin
    print(f"[DEBUG] Chemin Excel défini dans verification: {chemin_equipement}")


def verifier_commandes(username, password, commands, ip_list=None):
    logs = []

    if not chemin_equipement:
        logs.append("❌ Aucun fichier Excel sélectionné.")
        return logs

    if not commands:
        logs.append("❌ Aucune commande à vérifier.")
        return logs

    try:
        workbook = openpyxl.load_workbook(chemin_equipement)
        sheet = workbook.active
    except Exception as e:
        logs.append(f"❌ Erreur lecture Excel : {str(e)}")
        return logs

    # Traitement des IPs spécifiques si fournies
    specific_ips = []
    if ip_list:
        specific_ips = [ip.strip() for ip in ip_list.split(',') if ip.strip()]

    for row in sheet.iter_rows(min_row=4, values_only=True):
        if len(row) < 4:  # Vérifier si la ligne a suffisamment de colonnes
            continue

        hostname, ip, equipement_type, configurer = row[:4]  # Prendre seulement les 4 premières colonnes

        # Filtrer selon les IPs spécifiques si fournies
        if specific_ips and ip not in specific_ips:
            continue

        # Vérifier que les champs requis ne sont pas vides
        if not all([hostname, ip, equipement_type]):
            continue

        logs.append(f"\n[🔍 {hostname} ({ip})]")
        logs.append("🔌 Tentative de connexion...")

        try:
            connection = ConnectHandler(
                device_type=equipement_type,
                host=ip,
                username=username,
                password=password,
                secret=password,
                timeout=10
            )

            logs.append(f"✅ Connecté ({connection.find_prompt()})")
            connection.enable()
            config = connection.send_command("show running-config")

            found = []
            for cmd in commands:
                cmd = cmd.strip()
                if not cmd:
                    continue

                logs.append(f"🔎 Recherche: {cmd}")
                if cmd.lower() in config.lower():
                    logs.append(f"   ✅ Trouvé: {cmd}")
                    found.append(cmd)
                else:
                    logs.append(f"   ❌ Non trouvé: {cmd}")

            logs.append("\n📊 Résumé pour cet équipement:")
            logs.append(f"Commandes trouvées ({len(found)}):")
            for cmd in found:
                logs.append(f"  - {cmd}")

            connection.disconnect()

        except Exception as e:
            error_msg = str(e)
            if "TCP connection to device failed" in error_msg:
                logs.append(f"❌ Erreur: {error_msg}\n\nCommon causes of this problem are:\n"
                            "1. Incorrect hostname or IP address.\n"
                            "2. Wrong TCP port.\n"
                            "3. Intermediate firewall blocking access.\n\n"
                            f"Device settings: {equipement_type} {ip}:22")
            elif "Unsupported 'device_type'" in error_msg:
                logs.append(f"❌ Erreur: {error_msg}")
            else:
                logs.append(f"❌ Erreur: {error_msg}")

    return logs