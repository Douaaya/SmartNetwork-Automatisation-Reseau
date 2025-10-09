import pandas as pd
import nmap
import ipaddress
from datetime import datetime
import subprocess
import socket
import json
import os
from typing import List, Dict, Union, Optional


class NetworkScanner:
    def __init__(self, excel_path: str = None):
        """Initialise le scanner avec chemin Excel optionnel"""
        self.nm = nmap.PortScanner()
        self.excel_path = excel_path
        self.scan_results = []
        self.default_config = {
            'scan_types': {
                'discovery': {
                    'flags': '-sn',
                    'name': 'Découverte réseau (Ping)',
                    'description': 'Détecte simplement les hôtes actifs sans analyser les ports'
                },
                'quick': {
                    'flags': '-T4 -F',
                    'name': 'Scan rapide',
                    'description': 'Scan des 100 ports les plus communs rapidement'
                },
                'standard': {
                    'flags': '-sV -T4 -O --top-ports 100',
                    'name': 'Scan standard',
                    'description': 'Détection des services et OS sur les ports communs'
                },
                'full': {
                    'flags': '-p- -sV -O -T4',
                    'name': 'Scan complet',
                    'description': 'Scan exhaustif de tous les ports (peut être long)'
                }
            },
            'timeout': '30m',
            'host_timeout': '5m',
            'max_retries': 2,
            'disable_dns': True,
            'privileged': True,
            'log_file': 'scan_log.txt'
        }
        self.current_config = self.default_config.copy()

    def set_excel_path(self, path: str):
        """Définit le chemin du fichier Excel"""
        if path and os.path.exists(path):
            self.excel_path = path
            return True
        return False

    def load_config(self, config_path: str = 'scan_config.json') -> bool:
        """Charge la configuration depuis un fichier JSON"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.current_config.update(json.load(f))
                return True
            return False
        except Exception as e:
            print(f"Erreur chargement config: {e}")
            return False

    def validate_target(self, target: str) -> bool:
        """Valide une cible (IP, plage ou hostname)"""
        try:
            ipaddress.ip_network(target, strict=False)
            return True
        except ValueError:
            try:
                socket.gethostbyname(target)
                return True
            except socket.error:
                return False

    def execute_scan(self, target: str, scan_type: str = 'discovery') -> Dict:
        """
        Exécute un scan Nmap avec gestion robuste des erreurs

        Args:
            target: Adresse IP, plage ou hostname à scanner
            scan_type: Type de scan (discovery|quick|standard|full)

        Returns:
            Dictionnaire avec résultats ou erreur
        """
        if not self.validate_target(target):
            return {'error': f"Cible invalide: {target}", 'target': target}

        scan_info = self.current_config['scan_types'].get(scan_type, {})
        scan_flags = scan_info.get('flags', '-sn')

        try:
            command = [
                'nmap',
                *scan_flags.split(),
                target,
                f'--host-timeout {self.current_config["host_timeout"]}',
                f'--max-retries {self.current_config["max_retries"]}',
                '-oX -'  # Sortie XML vers stdout
            ]

            if self.current_config['disable_dns']:
                command.append('-n')
            if self.current_config['privileged']:
                command.append('--privileged')

            result = subprocess.run(
                ' '.join(command),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=int(self.current_config['timeout'][:-1]) * 60
            )

            if result.returncode != 0:
                return {'error': result.stderr, 'target': target}

            return self.parse_nmap_xml(result.stdout, target)

        except subprocess.TimeoutExpired:
            return {'error': 'Timeout global dépassé', 'target': target}
        except Exception as e:
            return {'error': str(e), 'target': target}

    def parse_nmap_xml(self, xml_output: str, target: str) -> Dict:
        """Parse la sortie XML de Nmap pour extraction structurée"""
        try:
            self.nm.analyse_nmap_xml_scan(xml_output)
            hosts = []

            # Gestion spéciale pour les scans de découverte
            if '-sn' in xml_output:  # Scan ping seulement
                if target in self.nm.all_hosts():
                    host_info = {
                        'ip': target,
                        'status': 'UP',
                        'scan_type': 'discovery',
                        'scan_time': datetime.now().isoformat()
                    }
                    hosts.append(host_info)
                else:
                    hosts.append({
                        'ip': target,
                        'status': 'DOWN',
                        'scan_type': 'discovery',
                        'scan_time': datetime.now().isoformat()
                    })
                return {'hosts': hosts, 'scan_type': 'discovery'}

            # Pour les autres types de scans
            for host in self.nm.all_hosts():
                host_info = {
                    'ip': host,
                    'hostname': self.nm[host].hostname() or '',
                    'status': self.nm[host].state(),
                    'scan_type': 'advanced',
                    'ports': [],
                    'os': {},
                    'scan_time': datetime.now().isoformat()
                }

                for proto in self.nm[host].all_protocols():
                    for port, port_info in self.nm[host][proto].items():
                        host_info['ports'].append({
                            'port': port,
                            'protocol': proto,
                            'state': port_info['state'],
                            'service': port_info.get('name', ''),
                            'version': port_info.get('version', '')
                        })

                if 'osmatch' in self.nm[host]:
                    host_info['os'] = {
                        'name': self.nm[host]['osmatch'][0]['name'],
                        'accuracy': self.nm[host]['osmatch'][0]['accuracy']
                    }

                hosts.append(host_info)

            return {'hosts': hosts, 'scan_type': 'advanced'}

        except Exception as e:
            return {'error': f"Erreur parsing XML: {str(e)}", 'target': target}

    def scan_from_excel(self, scan_type: str = 'discovery') -> Dict:
        """Scan des équipements listés dans le fichier Excel"""
        if not self.excel_path or not os.path.exists(self.excel_path):
            return {'error': 'Fichier Excel introuvable', 'action': 'redirect_home'}

        try:
            df = pd.read_excel(self.excel_path, header=2)
            results = {'hosts': [], 'errors': []}

            for _, row in df.iterrows():
                if pd.isna(row['IP Address']):
                    continue

                target = str(row['IP Address'])
                scan_result = self.execute_scan(target, scan_type)

                if 'error' in scan_result:
                    results['errors'].append({
                        'ip': target,
                        'hostname': row.get('Hostname', ''),
                        'error': scan_result['error']
                    })
                else:
                    for host in scan_result.get('hosts', []):
                        host['hostname'] = host.get('hostname', '') or row.get('Hostname', f"IP-{host['ip']}")
                        results['hosts'].append(host)

            return results

        except Exception as e:
            return {'error': f"Erreur scan Excel: {str(e)}"}

    def scan_ip_range(self, start_ip: str, end_ip: str, scan_type: str = 'discovery') -> Dict:
        """Scan d'une plage d'adresses IP"""
        try:
            start = ipaddress.IPv4Address(start_ip)
            end = ipaddress.IPv4Address(end_ip)

            results = {'hosts': [], 'errors': []}

            for ip_int in range(int(start), int(end) + 1):
                ip = str(ipaddress.IPv4Address(ip_int))
                scan_result = self.execute_scan(ip, scan_type)

                if 'error' in scan_result:
                    results['errors'].append({
                        'ip': ip,
                        'error': scan_result['error']
                    })
                else:
                    results['hosts'].extend(scan_result.get('hosts', []))

            return results

        except ipaddress.AddressValueError as e:
            return {'error': f"Plage IP invalide: {str(e)}"}

    def export_results(self, results: Dict, export_format: str = 'excel', file_path: str = None) -> bool:
        """Exporte les résultats dans différents formats"""
        if not results or not results.get('hosts'):
            return False

        if not file_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"scan_results_{timestamp}"

        try:
            df_data = []
            for host in results['hosts']:
                row = {
                    'Hostname': host.get('hostname', ''),
                    'IP': host.get('ip', ''),
                    'Status': host.get('status', ''),
                    'OS': host.get('os', {}).get('name', ''),
                    'Ports': len(host.get('ports', []))
                }
                df_data.append(row)

            df = pd.DataFrame(df_data)

            if export_format == 'excel':
                df.to_excel(f"{file_path}.xlsx", index=False)
                return True

            elif export_format == 'json':
                with open(f"{file_path}.json", 'w') as f:
                    json.dump(results, f, indent=4)
                return True

            elif export_format == 'html':
                df.to_html(f"{file_path}.html", index=False)
                return True

            return False

        except Exception as e:
            print(f"Erreur export: {str(e)}")
            return False