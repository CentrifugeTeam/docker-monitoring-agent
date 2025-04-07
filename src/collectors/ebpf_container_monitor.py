#
# from bcc import BPF
# import ctypes
# import time
# from docker import DockerClient
# from collections import defaultdict
# import os

# # Проверка прав
# if os.geteuid() != 0:
#   print("ERROR: This script must be run as root!")
#   print("Please run with sudo:")
#   print("sudo python3", __file__)
#   exit(1)

# # Конфигурация eBPF
# EBPF_PROGRAM = """
# #include <uapi/linux/ptrace.h>
# #include <linux/ip.h>
# #include <linux/tcp.h>
# #include <bcc/proto.h>

# // Структура для хранения данных о соединении
# struct conn_key_t {
#     u32 saddr;
#     u32 daddr;
#     u16 sport;
#     u16 dport;
# };
# BPF_HASH(conn_stats, struct conn_key_t);

# // Хук для входящих пакетов
# int trace_tcp_recv(struct __sk_buff *skb) {
#     // Проверка длины пакета
#     void *data = (void *)(long)skb->data;
#     void *data_end = (void *)(long)skb->data_end;

#     struct ethhdr *eth = data;
#     if ((void *)(eth + 1) > data_end) return 0;

#     // Пропускаем не-IP пакеты
#     if (eth->h_proto != htons(ETH_P_IP)) return 0;

#     struct iphdr *ip = (struct iphdr *)(eth + 1);
#     if ((void *)(ip + 1) > data_end) return 0;

#     // Пропускаем не-TCP пакеты
#     if (ip->protocol != IPPROTO_TCP) return 0;

#     struct tcphdr *tcp = (struct tcphdr *)(ip + 1);
#     if ((void *)(tcp + 1) > data_end) return 0;

#     // Заполняем ключ соединения
#     struct conn_key_t key = {
#         .saddr = ip->saddr,
#         .daddr = ip->daddr,
#         .sport = tcp->source,
#         .dport = tcp->dest
#     };

#     u64 *value = conn_stats.lookup_or_init(&key, &(u64){0});
#     (*value) += skb->len;

#     return 0;
# }
# """

# class ContainerTrafficMonitor:
#     def __init__(self):
#         self.client = DockerClient(base_url='unix:///var/run/docker.sock')
#         self.bpf = BPF(text=EBPF_PROGRAM)
#         self.bpf.attach_tracepoint(tp="net:netif_receive_skb", fn_name="trace_tcp_recv")

#         self.ip_to_container = {}
#         self.update_container_map()

#     def update_container_map(self):
#         """Обновляет маппинг IP-адресов на контейнеры"""
#         self.ip_to_container = {}
#         for container in self.client.containers.list():
#             networks = container.attrs['NetworkSettings']['Networks']
#             for net_name, net_settings in networks.items():
#                 if 'IPAddress' in net_settings:
#                     self.ip_to_container[net_settings['IPAddress']] = container.name

#     def ip_to_str(self, ip):
#         """Конвертирует 32-битный IP в строку"""
#         return f"{ip>>24&0xFF}.{ip>>16&0xFF}.{ip>>8&0xFF}.{ip&0xFF}"

#     def run(self, interval=5):
#         """Основной цикл мониторинга"""
#         try:
#             while True:
#                 self.update_container_map()
#                 print("\n[+] Current container network traffic:")

#                 container_stats = defaultdict(lambda: {'in': 0, 'out': 0})

#                 for key, value in self.bpf["conn_stats"].items():
#                     src_ip = self.ip_to_str(key.saddr)
#                     dst_ip = self.ip_to_str(key.daddr)

#                     src_container = self.ip_to_container.get(src_ip, "unknown")
#                     dst_container = self.ip_to_container.get(dst_ip, "unknown")

#                     if src_container != "unknown":
#                         container_stats[src_container]['out'] += value.value
#                     if dst_container != "unknown":
#                         container_stats[dst_container]['in'] += value.value

#                 for container, stats in container_stats.items():
#                     print(f"{container}: IN={stats['in']/1024:.2f}KB OUT={stats['out']/1024:.2f}KB")

#                 time.sleep(interval)

#         except KeyboardInterrupt:
#             print("\n[!] Stopping monitor...")

# if __name__ == "__main__":
#     monitor = ContainerTrafficMonitor()
#     monitor.run()

# --------------------------------------------------------------------------------


# from bcc import BPF
# import ctypes
# import time
# import os

# if os.geteuid() != 0:
#   print("Please run as root")
#   exit(1)

# EBPF_PROGRAM = """
# #include <uapi/linux/ptrace.h>

# BPF_HASH(syscall_count, u32);

# int count_syscalls(struct pt_regs *ctx) {
#     u32 key = 0;
#     u64 *value = syscall_count.lookup_or_init(&key, &(u64){0});
#     (*value)++;
#     return 0;
# }
# """

# try:
#     bpf = BPF(text=EBPF_PROGRAM)
#     bpf.attach_kprobe(event="__x64_sys_openat", fn_name="count_syscalls")

#     print("Monitoring syscalls... Ctrl+C to stop")
#     while True:
#         for k, v in bpf["syscall_count"].items():
#             print(f"Syscalls: {v.value}")
#         time.sleep(1)

# except Exception as e:
#     print(f"Error: {str(e)}")
#     print("Falling back to Docker API monitoring...")

#     # Альтернативный код с использованием Docker API
#     from docker import DockerClient
#     client = DockerClient(base_url='unix:///var/run/docker.sock')
#     while True:
#         for container in client.containers.list():
#             stats = container.stats(stream=False)
#             print(f"{container.name}: {stats['networks']}")
#         time.sleep(5)
