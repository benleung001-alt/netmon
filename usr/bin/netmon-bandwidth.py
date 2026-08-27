#!/usr/bin/env python3
"""实时带宽采样器：对 conntrack 双采样，计算设备 Mbps/Kbps"""
import re, sys, time, json
from collections import defaultdict

SAMPLE_SEC = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

def is_local(ip):
    p = ip.split('.')
    if len(p) != 4: return False
    f, s = int(p[0]), int(p[1])
    return f == 10 or (f == 172 and 16 <= s <= 31) or (f == 192 and s == 168)

def sample():
    ip_data = defaultdict(lambda: {'rx': 0, 'tx': 0, 'active': 0})
    try:
        with open('/proc/net/nf_conntrack') as f:
            for line in f:
                line = line.strip()
                src_m = re.search(r'src=([\d.]+)', line)
                dst_m = re.search(r'dst=([\d.]+)', line)
                bytes_m = re.search(r'bytes=(\d+)', line)
                state_m = re.search(r'\b(ESTABLISHED|SYN_SENT|NEW)\b', line)
                if not src_m or not dst_m or not bytes_m:
                    continue
                src_ip, dst_ip = src_m.group(1), dst_m.group(1)
                b = int(bytes_m.group(1))
                active = bool(state_m)
                if is_local(src_ip) and not is_local(dst_ip):
                    ip_data[src_ip]['rx'] += b
                    if active: ip_data[src_ip]['active'] += 1
                elif is_local(dst_ip) and not is_local(src_ip):
                    ip_data[dst_ip]['tx'] += b
                    if active: ip_data[dst_ip]['active'] += 1
    except Exception as e:
        print(f"采样错误: {e}", file=sys.stderr)
    return ip_data

print("采样中...", file=sys.stderr)
s1 = sample()
time.sleep(SAMPLE_SEC)
s2 = sample()

result = []
for ip in set(list(s1.keys()) + list(s2.keys())):
    rx_delta = max(0, s2[ip]['rx'] - s1[ip]['rx'])
    tx_delta = max(0, s2[ip]['tx'] - s1[ip]['tx'])
    rx_bps = rx_delta * 8 / SAMPLE_SEC
    tx_bps = tx_delta * 8 / SAMPLE_SEC
    result.append({
        'ip': ip,
        'rx_bps': round(rx_bps, 2),
        'tx_bps': round(tx_bps, 2),
        'total_bps': round(rx_bps + tx_bps, 2),
        'active_flows': s2[ip]['active'],
    })

result.sort(key=lambda x: x['total_bps'], reverse=True)
output = {
    'generated': time.time(),
    'sample_sec': SAMPLE_SEC,
    'devices': result,
}
print(json.dumps(output, indent=2))
