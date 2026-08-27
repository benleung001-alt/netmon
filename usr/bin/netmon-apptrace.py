#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NetMon App 追踪 —— 识别抖音/小红书/微信等 App 使用情况及流量"""
import re, sys, time, json, subprocess
from collections import defaultdict

# App 域名关键词（匹配子域名）
APP_DOMAINS = {
    '抖音': ['douyin', 'snssdk', 'amemv', 'bytegoofy', 'iesdouyin', 'bytedance'],
    '小红书': ['xiaohongshu', 'edith', 'xhslink', 'xhsdiscover'],
    '微信': ['weixin', 'wechat', 'tenpay', 'qq.com', 'tencent.com'],
    '支付宝': ['alipay', 'alibaba', 'antfin'],
    '淘宝': ['taobao', 'tmall', 'aliexpress'],
    '抖音火山版': ['huoshan', 'veo'],
    '今日头条': ['toutiao', 'jrtoutiao'],
}

def is_local(ip):
    p = ip.split('.')
    if len(p) != 4: return False
    f, s = int(p[0]), int(p[1])
    return f == 10 or (f == 172 and 16 <= s <= 31) or (f == 192 and s == 168)

def get_dns_log():
    """从 logread 获取 DNS 查询日志（最近 500 条）"""
    queries = []
    try:
        # logread 不支持 -i，改用 -l 限制条数
        result = subprocess.run(['logread', '-e', 'dnsmasq', '-l', '1000'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            # 格式: query[A] douyin.com from 192.168.6.170
            m = re.search(r'query\[[A*]\]\s+(\S+)\s+from\s+([\d.]+)', line)
            if m:
                domain = m.group(1).lower()
                ip = m.group(2)
                queries.append((ip, domain))
    except:
        pass
    return queries

def classify_domain(domain):
    """根据域名判断是什么 App"""
    for app_name, keywords in APP_DOMAINS.items():
        for kw in keywords:
            if kw in domain:
                return app_name
    return None

def get_conntrack_stats():
    """从 conntrack 获取设备流量统计"""
    ip_data = defaultdict(lambda: {'rx': 0, 'tx': 0, 'active': 0, 'flows': 0})
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
                    ip_data[src_ip]['flows'] += 1
                    if active: ip_data[src_ip]['active'] += 1
                elif is_local(dst_ip) and not is_local(src_ip):
                    ip_data[dst_ip]['tx'] += b
                    if active: ip_data[dst_ip]['active'] += 1
    except Exception as e:
        print(f"读取 conntrack 失败: {e}", file=sys.stderr)
    return ip_data

def get_leases():
    """读取 DHCP 租约"""
    leases = {}
    try:
        with open('/tmp/dhcp.leases') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    mac, ip, host = parts[1], parts[2], parts[3]
                    if host != '*':
                        leases[ip] = {'mac': mac, 'hostname': host}
    except:
        pass
    return leases

def main():
    print("采样中...", file=sys.stderr)
    
    # 获取 DNS 查询日志（最近）
    dns_queries = get_dns_log()
    
    # 按 IP 统计 App 使用
    device_apps = defaultdict(lambda: defaultdict(int))
    for ip, domain in dns_queries:
        if is_local(ip):
            app = classify_domain(domain)
            if app:
                device_apps[ip][app] += 1
    
    # 获取 conntrack 流量统计
    conntrack = get_conntrack_stats()
    
    # 获取 DHCP 租约
    leases = get_leases()
    
    # 合并输出
    output = {
        'generated': time.time(),
        'dns_samples': len(dns_queries),
        'devices': []
    }
    
    # 遍历所有有 DNS 记录的设备
    all_ips = set(list(device_apps.keys()) + list(conntrack.keys()) + list(leases.keys()))
    
    for ip in sorted(all_ips, key=lambda x: (conntrack.get(x, {}).get('rx', 0) + conntrack.get(x, {}).get('tx', 0)), reverse=True):
        if not is_local(ip):
            continue
            
        lease = leases.get(ip, {})
        hostname = lease.get('hostname', '未知')
        mac = lease.get('mac', '')
        
        ct = conntrack.get(ip, {})
        rx = ct.get('rx', 0)
        tx = ct.get('tx', 0)
        active = ct.get('active', 0)
        flows = ct.get('flows', 0)
        
        apps = device_apps.get(ip, {})
        
        # 只输出有 App 使用或活跃的设备
        if apps or active > 0:
            output['devices'].append({
                'ip': ip,
                'mac': mac,
                'hostname': hostname,
                'rx_bytes': rx,
                'tx_bytes': tx,
                'total_bytes': rx + tx,
                'active_flows': active,
                'total_flows': flows,
                'apps': dict(apps) if apps else {},
                'app_total_bytes': sum(apps.values()) if apps else 0,
            })
    
    # 添加全局 App 统计
    global_apps = defaultdict(lambda: {'count': 0, 'devices': set()})
    for ip, apps in device_apps.items():
        for app, count in apps.items():
            global_apps[app]['count'] += count
            global_apps[app]['devices'].add(ip)
    
    output['global_apps'] = {
        app: {'queries': stats['count'], 'devices': len(stats['devices'])}
        for app, stats in global_apps.items()
    }
    
    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
