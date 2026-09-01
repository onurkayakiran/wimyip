import random
import socket
import time

try:
    from scapy.all import IP, TCP, conf, sr1

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

POPULAR_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 161, 162,
    389, 386, 427, 443, 445, 465, 514, 515, 587, 631, 636, 646,
    873, 993, 995, 1080, 1433, 1434, 1521, 2049, 3306, 3389,
    5432, 5900, 5901, 6379, 6443, 8000, 8001, 8008, 8080, 8443,
    8888, 9090, 9200, 9300, 9416, 9600, 10000, 27017, 27018,
]

SERVICE_MAP = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPCBind", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    465: "SMTPS", 514: "Syslog", 587: "SMTP", 631: "IPP", 636: "LDAPS",
    993: "IMAPS", 995: "POP3S", 1080: "SOCKS", 1433: "MSSQL",
    1434: "MSSQL Browser", 1521: "Oracle DB", 2049: "NFS", 3306: "MySQL",
    3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
    8000: "HTTP Alt", 8080: "HTTP Proxy", 8443: "HTTPS Alt",
    8888: "HTTP Alt", 9090: "Web Console", 9200: "Elasticsearch",
    27017: "MongoDB", 27018: "MongoDB",
}


class ScannerConfig:
    def __init__(self, subnet, port_mode="popular", custom_ports=None,
                 delay=0.01, timeout=1,
                 enable_service_detect=True, syn_scan=True):
        self.subnet = subnet
        self.port_mode = port_mode
        self.custom_ports = custom_ports or []
        self.delay = delay
        self.timeout = timeout
        self.enable_service_detect = enable_service_detect
        self.syn_scan = syn_scan


class ServiceDetector:
    """Acik portta calisan hizmeti tespit eder"""

    @staticmethod
    def get_service_info(ip, port):
        info = {
            "port": port, "ip": ip, "services": [], "banner": None,
            "http_title": None, "ssl_info": None, "protocol": None,
        }
        try:
            banner = ServiceDetector.banner_grab(ip, port)
            if banner:
                info["banner"] = banner[:500]

            http_info = ServiceDetector.check_http_service(ip, port)
            if http_info:
                info["services"].append(http_info.get("service", "HTTP"))
                info["http_title"] = http_info.get("title")
                info["protocol"] = "http"

            if port in [443, 8443, 9443, 8000, 8080] or "ssl" in str(info.get("banner", "")):
                ssl_info = ServiceDetector.get_ssl_info(ip, port)
                if ssl_info:
                    info["ssl_info"] = ssl_info

            service_name = SERVICE_MAP.get(port)
            if service_name:
                if not any("Known" in s for s in info["services"]):
                    info["services"].append(f"{service_name} (Bilinen Port)")

            if not info["services"]:
                probe_result = ServiceDetector.tcp_probe(ip, port)
                if probe_result:
                    info["services"].append(probe_result.get("type", "Bilinmeyen Servis"))
                    if probe_result.get("banner"):
                        info["banner"] = probe_result["banner"][:500]

            if not info["services"]:
                info["services"].append(f"Port {port} - Acik (Servis belirlenemedi)")

        except Exception as e:
            info["error"] = str(e)

        return info

    @staticmethod
    def banner_grab(ip, port, timeout=3):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))

            if port in [80, 8080, 8000, 8443]:
                try:
                    sock.sendall(b"HEAD / HTTP/1.1\r\nHost: " + ip.encode() + b"\r\nConnection: close\r\n\r\n")
                    response = sock.recv(4096).decode("utf-8", errors="ignore")
                    sock.close()

                    for line in response.split("\r\n"):
                        if line.lower().startswith("server:"):
                            return f"HTTP - {line.strip()}"
                        elif line.lower().startswith("x-powered-by:"):
                            return f"{response[:200]}"

                    if response and "HTTP/" in response:
                        return f"HTTP Servisi - {response[:200]}"
                except Exception:
                    pass

            time.sleep(0.5)
            try:
                sock.settimeout(1)
                banner = sock.recv(1024).decode("utf-8", errors="ignore")
                sock.close()
                if banner and len(banner.strip()) > 0:
                    return banner[:300]
            except Exception:
                pass

            sock.close()
        except Exception:
            pass
        return None

    @staticmethod
    def check_http_service(ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((ip, port))

            request = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {ip}\r\n"
                f"User-Agent: Mozilla/5.0 ScannerBot\r\n"
                f"Accept: text/html\r\n"
                f"Connection: close\r\n\r\n"
            )
            sock.sendall(request.encode())

            response_data = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                    if b"</html>" in response_data or len(response_data) > 50000:
                        break
            except Exception:
                pass

            sock.close()

            response = response_data.decode("utf-8", errors="ignore")
            if "HTTP/" not in response:
                return None

            title = None
            html_response = response.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in response else ""
            if "<title>" in html_response.lower():
                import re

                match = re.search(r"<title[^>]*>(.*?)</title>", html_response, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()

            headers_part = response.split("\r\n\r\n", 1)[0] if "\r\n\r\n" in response else ""
            server = None
            for line in headers_part.split("\n"):
                if line.lower().startswith("server:"):
                    server = line.split(":", 1)[1].strip()

            result = {"service": "HTTP", "port": port}
            if title:
                result["title"] = title[:200]
            if server:
                result["server"] = server
            return result

        except Exception:
            return None

    @staticmethod
    def get_ssl_info(ip, port, timeout=3):
        try:
            import ssl

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            ssl_sock = context.wrap_socket(sock, server_hostname=ip)

            cert = ssl_sock.getpeercert()
            ssl_sock.close()

            if cert:
                info = {
                    "version": cert.get("version", "Bilinmiyor"),
                    "serialNumber": cert.get("serialNumber", ""),
                    "notBefore": cert.get("notBefore", ""),
                    "notAfter": cert.get("notAfter", ""),
                    "subject": str(cert.get("subject", "")),
                    "issuer": str(cert.get("issuer", "")),
                    "subjectAltName": cert.get("subjectAltName", []),
                }

                for attr_list in cert.get("subject", []):
                    if attr_list[0] == "commonName":
                        info["cn"] = attr_list[1]

                return info

        except Exception:
            pass
        return None

    @staticmethod
    def tcp_probe(ip, port, timeout=3):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))

            probes = [
                (b"\r\n", "Telnet/SSH"),
                (b"QSTAT\r\n", "Quake Server"),
                (b"stat\r\n", "Minecraft"),
            ]

            for data, probe_type in probes:
                try:
                    sock.sendall(data)
                    time.sleep(0.5)
                    sock.settimeout(1)
                    response = sock.recv(1024).decode("utf-8", errors="ignore")
                    if response and len(response.strip()) > 0:
                        return {"type": probe_type, "banner": response[:300]}
                except Exception:
                    continue

            sock.close()
            return None

        except Exception:
            return None


_SCAPY_WORKING = False
if SCAPY_AVAILABLE:
    try:
        _test_pkt = IP(dst="127.0.0.1") / TCP(sport=12345, dport=1, flags="S")
        sr1(_test_pkt, timeout=0.5, verbose=0, chainCC=True, retry=0)
        _SCAPY_WORKING = True
    except Exception:
        _SCAPY_WORKING = False


class PortScanner:
    def __init__(self, config):
        self.config = config
        if SCAPY_AVAILABLE and _SCAPY_WORKING:
            conf.verb = 0
            conf.timeout = max(config.timeout * 0.8, 1)

    def get_ports_to_scan(self):
        if self.config.port_mode == "custom":
            return sorted(set(self.config.custom_ports))
        elif self.config.port_mode == "popular":
            return POPULAR_PORTS[:]
        elif self.config.port_mode == "all":
            return list(range(1, 65536))
        else:
            return POPULAR_PORTS[:]

    def scan_ip_port_syn(self, ip, port):
        result = {"ip": ip, "port": port, "state": "filtered", "service": None}

        if not SCAPY_AVAILABLE:
            return self._fallback_scan(ip, port)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                pkt = IP(dst=ip) / TCP(sport=random.randint(1024, 65535), dport=port, flags="S")
                current_timeout = self.config.timeout if attempt == 0 else max(self.config.timeout * 1.5, 2)

                resp = sr1(pkt, timeout=current_timeout, verbose=0, chainCC=True)

                if resp is None:
                    if attempt < max_retries - 1:
                        time.sleep(0.1)
                        continue
                    result["state"] = "filtered"
                    return result

                if resp.haslayer(TCP):
                    tcp_layer = resp[TCP]
                    if tcp_layer.flags == 0x12:
                        result["state"] = "open"
                        ack_pkt = IP(dst=ip) / TCP(sport=pkt[TCP].sport, dport=port, flags="A")
                        sr1(ack_pkt, timeout=current_timeout, verbose=0, chainCC=True)

                        rst_pkt = IP(dst=ip) / TCP(sport=pkt[TCP].sport, dport=port, flags="R")
                        sr1(rst_pkt, timeout=current_timeout, verbose=0, chainCC=True)
                        return result
                    elif tcp_layer.flags == 0x14:
                        result["state"] = "closed"
                        return result
                if attempt < max_retries - 1:
                    time.sleep(0.1)

            except Exception:
                if attempt >= max_retries - 1:
                    result["state"] = "filtered"

        return result

    def scan_ip_port_connect(self, ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)

            sock.setblocking(False)
            connect_result = sock.connect_ex((ip, port))

            if connect_result != 0 and connect_result not in (0, 115):
                sock.close()
                return {"ip": ip, "port": port, "state": "closed"}

            if connect_result == 115:
                time.sleep(0.1)
                err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err == 0:
                    sock.close()
                    return {"ip": ip, "port": port, "state": "open"}
                else:
                    sock.close()
                    return {"ip": ip, "port": port, "state": "closed"}

            sock.setblocking(True)
            sock.settimeout(self.config.timeout)

            if connect_result == 0:
                sock.close()
                return {"ip": ip, "port": port, "state": "open"}
            else:
                sock.close()
                return {"ip": ip, "port": port, "state": "closed"}

        except socket.timeout:
            try:
                sock.setblocking(True)
                sock.close()
            except Exception:
                pass
            return {"ip": ip, "port": port, "state": "filtered"}
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            return {"ip": ip, "port": port, "state": "filtered"}

    def _fallback_scan(self, ip, port):
        return self.scan_ip_port_connect(ip, port)

    def scan_single_ip(self, ip, ports_to_scan):
        ip_open_ports = []
        use_syn = self.config.syn_scan and SCAPY_AVAILABLE and _SCAPY_WORKING
        scan_method = self.scan_ip_port_syn if use_syn else self.scan_ip_port_connect

        for i, port in enumerate(ports_to_scan):
            result = scan_method(ip, port)

            if result["state"] == "open":
                ip_open_ports.append(port)
                time.sleep(self.config.delay * 3)
            elif i > 0 and i % 10 == 0:
                if self.config.delay > 0:
                    time.sleep(self.config.delay * 2)

        service_info_list = []
        if ip_open_ports and self.config.enable_service_detect:
            for port in ip_open_ports:
                svc_info = ServiceDetector.get_service_info(ip, port)
                service_info_list.append(svc_info)

        return {
            "ip": ip,
            "open_ports": ip_open_ports,
            "services": service_info_list,
            "total_scanned": len(ports_to_scan),
        }


def process_port_scan_item(item: dict, meta: dict) -> dict:
    config = ScannerConfig(
        subnet=item["ip"],
        port_mode=meta.get("port_mode", "custom"),
        custom_ports=meta.get("custom_ports") or [],
        # Port-ici (portlar arasi) gecikme - job.meta["delay_seconds"] (IP'ler
        # ARASI bekleme) ile KARISTIRILMAMALI, o worker.py'nin run_once'unda
        # ayrica uygulanıyor. Bu deger admin panelinden hic expose edilmiyor.
        delay=0.05,
        timeout=meta.get("timeout", 1.0),
        enable_service_detect=meta.get("enable_service_detect", True),
        syn_scan=meta.get("syn_scan", True),
    )
    scanner = PortScanner(config)
    return scanner.scan_single_ip(item["ip"], scanner.get_ports_to_scan())
