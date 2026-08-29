#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NetMon App 追踪 —— 识别主流 App 使用情况及流量（基于 DNS 查询日志）"""
import re, sys, time, json, subprocess
from collections import defaultdict

# ═══════════════════════════════════════════════════════════
# App 域名关键词库（匹配子域名）—— 持续扩充中
# 格式：App 中文名 → [关键词列表，任意一个命中即判定]
# 注意：关键词用小写，匹配时不区分大小写
# ═══════════════════════════════════════════════════════════
APP_DOMAINS = {
    # ── 社交通讯 ──────────────────────────────────────────
    '微信': ['weixin', 'wechat', 'tenpay', 'wx', 'mmstat', 'weixin.qq', 'wechatpay'],
    'QQ': ['qq.com', 'tencent.com', 'qqmusic', 'tencentmusic', 'qqmail', 'foxmail'],
    '微博': ['weibo', 'weibocdn', 'sinaimg', 'sinajs', 'sina.com.cn'],
    '钉钉': ['dingtalk', 'dingding', 'alicdn'],
    '飞书': ['feishu', 'byteimg', 'bytedanceimg'],
    '企业微信': ['wework', 'work.weixin'],

    # ── 短视频 / 直播 ─────────────────────────────────────
    '抖音': ['douyin', 'snssdk', 'amemv', 'iesdouyin', 'bytegoofy', 'bytedance', 'bytecdn'],
    '快手': ['ksord', 'kuaishou', 'kwai', 'kssrc', 'kscdn'],
    '哔哩哔哩': ['bilibili', 'bilibili.com', 'bilivideo', 'b23', 'biliapi', 'hdslb', 'biliimg'],
    '小红书': ['xiaohongshu', 'edith', 'xhslink', 'xhsdiscover', 'xhsdata'],
    '西瓜视频': ['ixigua', 'snssdk', 'byteimg'],

    # ── 直播 / 娱乐 ───────────────────────────────────────
    '斗鱼': ['douyucdn', 'douyu.com', 'douyuyyds'],
    '虎牙': ['huya', 'huya.com'],
    'YY语音': ['yy.com', 'yyioe'],
    '花椒': ['huajiao', 'huajiaostatic'],

    # ── 音乐 / 音频 ───────────────────────────────────────
    'QQ音乐': ['qqmusic', 'y.qq.com', 'music.tc'],
    '网易云音乐': ['163.com', '163cn.fm', 'music.163', 'netease'],
    '咪咕音乐': ['migu.cn', 'miguvideo'],
    '喜马拉雅': ['himalaya', 'xmcdn', 'xmlyaudio'],
    '蜻蜓FM': ['qingting', 'qingtingfm'],

    # ── 购物 / 支付 ───────────────────────────────────────
    '淘宝': ['taobao', 'tmall', 'aliexpress', 'lazada', 'ucweb'],
    '天猫': ['tmall', 'tianmao'],
    '支付宝': ['alipay', 'alibaba', 'antfin', 'antcloud'],
    '京东': ['jd.com', 'jd.hk', '360buy', 'whalepay'],
    '拼多多': ['pinduoduo', 'ppdai', 'ddpic'],
    '美团': ['meituan', 'meituan.com', 'meituan.net', 'dianping', 'dpfile'],
    '大众点评': ['dianping', 'dpfile'],
    '饿了么': ['ele.me', 'meituan'],
    '抖音火山版': ['huoshan', 'veo', 'snssdk'],
    '今日头条': ['toutiao', 'jrtoutiao', 'toutiaoimg'],

    # ── 办公 / 效率 ───────────────────────────────────────
    'WPS': ['wps.cn', 'wps.com', 'kdocs.cn', 'wpscdn', 'wpsimage', 'wpslogin', 'qwps'],
    '腾讯文档': ['docs.qq.com', 'tencent.com', 'qq.com'],
    '腾讯会议': ['meeting.tencent.com', 'tencentroom', 'tmelive'],
    '石墨文档': ['shimo.im', 'shimocdn'],
    '飞书': ['feishu.cn', 'feishu.io', 'byteimg'],
    '微软': ['microsoft.com', 'office.com', 'office365', 'live.com', 'msn.com',
              'windows.net', 'azureedge', 'copilot.microsoft', 'copilot.tencent'],

    # ── 出行 / 本地生活 ───────────────────────────────────
    '滴滴出行': ['didiglobal', 'didiall', 'diدي.com', 'di.com'],
    '高德地图': ['amap.com', 'autonavi', 'gaode.com'],
    '百度地图': ['baidu.com', 'bdstatic', 'baidupcs', 'emap.baidu'],
    '美团外卖': ['meituan.com', 'meituan.net'],
    '携程': ['ctrip', 'trip.com', 'ctrip.com', 'ctripimg'],
    '去哪儿': ['qunar', 'qunarimg', 'kun Bing'],

    # ── 视频 / 影视 ───────────────────────────────────────
    '优酷': ['youku', 'aliyuncs.com', 'ucweb', 'ucstat'],
    '爱奇艺': ['iqiyi', 'qidichannel', 'ppsimg', '71.am'],
    '腾讯视频': ['v.qq.com', 'tencentvideo', 'gtimg', 'qpic', 'qqvideo'],
    '芒果TV': ['mgtv.com', 'mangguo', 'mgtvcdn'],
    '搜狐视频': ['sohu.com', 'sohucs', 'tv.sohu'],
    '乐视': ['letv', 'letvcloud', 'lezhi'],

    # ── 游戏 ──────────────────────────────────────────────
    '腾讯游戏': ['tencent.com', 'tencentgames', 'tgp', 'tencentmusic', 'lol.qq', 'wegame'],
    '网易游戏': ['netease.com', '163.com', 'neteasecorp'],
    '米哈游': ['miHoYo', 'mihoyo', 'hoYoverse', 'honkaitact', 'hoeglobal'],
    '原神': ['genshin', 'miHoYo', 'mihoyo'],
    '王者荣耀': ['tencent.com', 'lol.qq', 'weiyun.com'],
    '和平精英': ['tencent.com', 'tgp'],

    # ── 金融 / 银行 ───────────────────────────────────────
    '招商银行': ['cmbchina', 'cmbimg', 'cmbwingchi'],
    '建设银行': ['ccb.com', 'ccbimg'],
    '工商银行': ['icbc.com.cn', 'icbcimg'],
    '支付宝理财': ['alipay', 'antfin'],

    # ── 浏览器 / 下载 ─────────────────────────────────────
    'UC浏览器': ['ucweb', 'uc.cn', 'ucstat'],
    '夸克': ['quark.cn', 'quarkcdn'],
    '迅雷': ['xunlei.com', 'xldns', 'thunder'],

    # ── 工具 / 系统 ───────────────────────────────────────
    '搜狗输入法': ['sogou.com', 'sogoucdn'],
    '百度输入法': ['baidu.com', 'bdstatic'],
    '苹果': ['apple.com', 'icloud.com', 'cdn-apple.com', 'mzstatic',
             'itunes.apple', 'appldnld', 'appstore'],
    'Google': ['google.com', 'googleapis.com', 'gstatic.com', 'android.com',
               'gmail.com', 'youtube.com', 'ytimg', 'googlevideo', 'gcp.gvt2'],
    'Synology': ['synology.com', 'synologyupdate', 'synocdn'],
}

# App 品牌色（供前端展示）
APP_COLORS = {
    '微信': '#07c160', 'QQ': '#12b7f5', '微博': '#e6162d',
    '抖音': '#fe2c55', '快手': '#ff4906', '哔哩哔哩': '#fb7299',
    '小红书': '#ff2442', '美团': '#ffc300', '淘宝': '#ff5000',
    '支付宝': '#1677ff', '京东': '#e1251b', '拼多多': '#e02e24',
    'WPS': '#c41d2e', '优酷': '#fffbe3', '爱奇艺': '#00aeec',
    '腾讯视频': '#00aeec', '今日头条': '#ff4500', '抖音火山版': '#ff6b00',
    '苹果': '#555555', 'Google': '#4285f4', '钉钉': '#3089ff',
    '飞书': '#3370ff', '搜狗输入法': '#00a8e6',
    'UC浏览器': '#ff6600', '夸克': '#0066ff',
}


def is_local(ip):
    p = ip.split('.')
    if len(p) != 4: return False
    f, s = int(p[0]), int(p[1])
    return f == 10 or (f == 172 and 16 <= s <= 31) or (f == 192 and s == 168)

def get_dns_log():
    """从 logread 获取 DNS 查询日志（最近 3000 条，扩大采样窗口）"""
    queries = []
    try:
        result = subprocess.run(['logread', '-e', 'dnsmasq', '-l', '3000'],
                                capture_output=True, text=True, timeout=8)
        for line in result.stdout.splitlines():
            m = re.search(r'query\[[A*MX]+\]\s+(\S+)\s+from\s+([\d.]+)', line)
            if m:
                domain = m.group(1).lower()
                ip = m.group(2)
                queries.append((ip, domain))
    except Exception as e:
        print(f"读取 DNS 日志失败: {e}", file=sys.stderr)
    return queries

def classify_domain(domain):
    """根据域名判断是什么 App（返回最匹配的 App 名，无匹配返回 None）"""
    matches = []
    for app_name, keywords in APP_DOMAINS.items():
        for kw in keywords:
            if kw in domain:
                matches.append((app_name, len(domain) - len(domain.replace(kw, '')), kw))
    if not matches:
        return None
    # 优先匹配更长、更具体的关键词
    matches.sort(key=lambda x: (-x[1], x[2]))
    return matches[0][0]

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
    dns_queries = get_dns_log()
    device_apps = defaultdict(lambda: defaultdict(int))

    for ip, domain in dns_queries:
        if is_local(ip):
            app = classify_domain(domain)
            if app:
                device_apps[ip][app] += 1

    conntrack = get_conntrack_stats()
    leases = get_leases()

    output = {
        'generated': time.time(),
        'dns_samples': len(dns_queries),
        'device_apps_raw': dict(device_apps),
        'devices': []
    }

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
