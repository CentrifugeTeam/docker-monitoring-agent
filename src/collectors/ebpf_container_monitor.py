from scapy.all import sniff, IP, TCP, ICMP
import platform
import subprocess
from typing import List
import docker

def get_docker_interfaces() -> List[str]:
    """Получаем список интерфейсов, связанных с Docker"""
    system = platform.system()

    if system == "Linux":
        # На Linux слушаем docker0 или veth-интерфейсы
        try:
            result = subprocess.run(
                "ip -o link show | awk -F': ' '{print $2}' | grep -E '^docker|^veth'",
                shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return result.stdout.splitlines()
        except subprocess.CalledProcessError:
            return ["docker0"]  # Fallback

    elif system == "Darwin":  # macOS
        # На macOS Docker использует utun-интерфейсы
        try:
            result = subprocess.run(
                "ifconfig | grep -o 'utun[0-9]' | sort -u",
                shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return result.stdout.splitlines() or ["lo0"]  # Fallback на loopback
        except subprocess.CalledProcessError:
            return ["lo0"]

    else:
        raise NotImplementedError(f"Unsupported OS: {system}")

def packet_callback(packet):
    """Обработчик пакетов"""
    if packet.haslayer(IP):
        ip_src = packet[IP].src
        ip_dst = packet[IP].dst
        if ip_src.startswith("172.") or ip_dst.startswith("172."):  # Docker сети обычно 172.x.x.x
            print(f"📦 Packet: {ip_src} → {ip_dst} | {packet.summary()}")

def monitor_docker_traffic():
    """Запуск сниффера"""
    interfaces = get_docker_interfaces()
    print(f"🔎 Monitoring Docker traffic on: {interfaces}")

    try:
        sniff(iface=interfaces, prn=packet_callback, store=False)
    except PermissionError:
        print("❌ Error: Need root privileges! Run with `sudo`.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    monitor_docker_traffic()
