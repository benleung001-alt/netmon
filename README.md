# NetMon · DHCP 设备清单模块（OpenWrt / Cudy TR3000）

把路由器上的 `/tmp/dhcp.leases` + `/proc/net/nf_conntrack` + dnsmasq DNS 日志自动解析成**带主机名、厂商、随机 MAC 标记、实时速率、App 使用追踪**的设备清单，并提供 OpenWrt LuCI 网页（NetMon 设备清单）。

## 文件清单与路由器部署路径

| 本仓库文件 | 部署到路由器 | 说明 |
|---|---|---|
| `usr/bin/netmon-devices` | `/usr/bin/netmon-devices` | 基础设备脚本（DHCP 租约 + OUI 查库，输出 JSON） |
| `usr/bin/netmon-devices.awk` | `/usr/bin/netmon-devices.awk` | awk JSON 合并逻辑 |
| `usr/bin/netmon-unified` | `/usr/bin/netmon-unified` | **v2 统一脚本**：合并设备清单 + conntrack 实时流量 + App 端口分类 |
| `usr/bin/netmon-bandwidth.py` | `/usr/bin/netmon-bandwidth.py` | 带宽采样器（对 conntrack 双采样，输出实时 Kbps/Mbps） |
| `usr/bin/netmon-apptrace.py` | `/usr/bin/netmon-apptrace.py` | **v3 App 追踪**：通过 DNS 日志识别抖音/小红书/微信等 App 使用情况 |
| `usr/bin/netmon-report` | `/usr/bin/netmon-report` | **v5 每日采集**：合并设备+App 生成按日期快照（JSON+MD）到 `/etc/netmon-reports/`，由 cron 23:30 触发 |
| `usr/share/netmon/oui.txt` | `/usr/share/netmon/oui.txt` | 精简 OUI→厂商 文本库（39984 条，1.2MB） |
| `usr/lib/lua/luci/controller/netmon.lua` | `/usr/lib/lua/luci/controller/netmon.lua` | LuCI 菜单挂载 |
| `usr/lib/lua/luci/view/netmon/devices.htm` | `/usr/lib/lua/luci/view/netmon/devices.htm` | LuCI 设备列表页（含流量 + App 标签） |

`gen_oui_txt.py` 是生成 `oui.txt` 的工具（从 mac-lookup 的 `oui-db.js` 提取），无需部署到路由器。

## 上传到路由器（二选一）

> 说明：NetMon 运行在路由器本地，模块文件需放到路由器存储里。

### 方式一 · `.ipk` 图形化安装（推荐，无需 SSH）
1. 把生成的 `netmon_1.0.1-1_all.ipk` 拷到你的电脑。
2. 登录路由器 LuCI → **系统 → 软件 → 上传软件包**，选该 `.ipk` 安装。
3. 装完自动赋权 + 重启 uhttpd，菜单立即生效。
> 若软件页提示空间不足（Cudy TR3000 128M 一般够用），在「系统 → 软件 → 配置」把软件源指向 overlay 或外挂 U 盘。

### 方式二 · `deploy.sh` 一键脚本（有 SSH 时）
```sh
# 在能 ssh 到路由器的终端（Git Bash / WSL / macOS / Linux）运行：
./deploy.sh                                  # 默认 192.168.1.1 / root
ROUTER_HOST=192.168.6.1 ./deploy.sh          # 自定义网关地址
```
脚本会自动 scp 全部文件、赋执行权限、重启 uhttpd，并跑一次 `netmon-devices` 验证输出。

## 使用方法

**方式 A · SSH 直接拿 JSON（最稳，便于接你自己的 netmon 后端）**
```sh
# v2 统一接口（设备 + 流量 + App 分类）
/usr/bin/netmon-unified
# 带宽采样（1 秒间隔，输出 Kbps/Mbps）
/usr/bin/netmon-bandwidth.py 1
# 基础设备清单（仅 DHCP + OUI）
/usr/bin/netmon-devices
```

**方式 B · LuCI 网页**
登录路由器管理页 → **状态 → NetMon 设备清单**（v5 界面），表格含：
- 主机名 / IP / MAC / 厂商 / 类型推断（带 emoji 图标：🍎💻📱📺🏠🔧）
- **在线状态**：在线设备置顶，绿色脉冲圆点 + 「在线」徽章；离线设备置灰
- **实时速率 ↓/↑**：每个设备每秒接收/发送速率（KB/s、MB/s），由 `netmon-unified` 对 conntrack 做差值计算
- **累计接收/发送流量**（来自 conntrack 累积字节）
- **活跃连接数**（ESTABLISHED/SYN_SENT 状态）
- **App 使用情况**（基于 DNS 查询：抖音/小红书/微信等，彩色标签 + 查询次数）
- 全局 App 使用排行（DNS 查询次数 + 占比条形 + 涉及设备数）
- 随机 MAC 红色徽章（带说明：iOS/Android 私有地址，无法追溯厂商）
- 顶部统计卡片 + 刷新倒计时进度条，每 15 秒自动刷新，响应式适配手机/电脑

## 每日采集报告

通过 `netmon-report` + cron，每天 **23:30** 自动生成一份快照，存到 `/etc/netmon-reports/`：

- `netmon-YYYY-MM-DD.json` —— 程序可读的完整数据（设备、流量、App 使用、全局排行）
- `netmon-YYYY-MM-DD.md` —— 人类可读表格报告（可直接发同事 / 存档）

每天一份，自动保留最近 **90 天**，更旧的自动清理。cron 任务由 `.ipk` 的 `postinst` 自动写入（或手动加一行 `30 23 * * * /usr/bin/netmon-report >> /etc/netmon-reports/cron.log 2>&1` 到 `/etc/crontabs/root` 并 `/etc/init.d/cron restart`）。

手动运行 / 查看历史：
```sh
/usr/bin/netmon-report                      # 立即生成今日报告
ls -1 /etc/netmon-reports/                  # 列出所有历史
cat /etc/netmon-reports/netmon-$(date +%F).md   # 看今天这份
```

## 数据来源与判定逻辑

- `/tmp/dhcp.leases`：dnsmasq 租约，字段 `到期时间戳 MAC IP 主机名 客户端ID`。主机名由设备自报，**不受随机 MAC 影响**——这是识别 iPhone/安卓最可靠的依据。
- `ip neigh` / `/proc/net/arp`：补充静态 IP / 非 DHCP 设备。
- **随机 MAC 判定**：MAC 第二 hex 字符为 `2/3/6/7/A/B/E/F` 即 U/L 位=1（本地管理/私有地址），标记 `random_mac=true`，厂商显示「私有地址(随机MAC)」，不查 OUI。
- **厂商查询**：真实 MAC 取前 6 位 OUI，在 `oui.txt` 中 grep 匹配（一次批量查询，几十台设备也很快）。
- **实时流量**：读取 `/proc/net/nf_conntrack`，对每个 conntrack 条目提取 `bytes=` 字段，按源/目的 IP 聚合。本地设备作为 src 时计 RX，作为 dst 时计 TX。
- **实时速率**：`netmon-unified` 把每次采样的总字节写入 `/tmp/netmon_state.json`，与上次采样做差值除以时间差，得出每个设备的 ↓/↑ 每秒速率（B/s、KB/s、MB/s）。
- **活跃连接**：conntrack 状态为 `ESTABLISHED`/`SYN_SENT`/`NEW` 的连接计数。
- **App 分类（v2）**：根据目标端口 dport 映射到应用名（443→HTTPS/QUIC、53→DNS、80→HTTP 等），未知端口显示 `Port-XXXX`。
- **App 追踪（v3）**：启用 dnsmasq `log-queries` 后，通过 DNS 查询日志识别抖音/小红书/微信/支付宝/淘宝等 App 使用情况。匹配域名关键词（`/etc/dnsmasq.apps`），统计各设备 App 查询次数并聚合到全局排行。

## 电脑端预览（无需路由器）

直接用浏览器打开 `preview.html`：
- 默认加载一组示例，可点「加载示例」/「解析」查看效果；
- 把路由器 `cat /tmp/dhcp.leases` 的内容粘进文本框点「解析」，即可在电脑上预览设备清单；
- 若与 `mac-lookup` 文件夹放在一起，会启用完整 OUI 库；否则用内置精简表（247 条常见厂商）。

## 已知限制

- 随机 MAC 设备无法反查真实厂商（这是 IEEE OUI 机制决定的，非 bug）；靠主机名识别。
- 纯静态 IP 且长期无通信的设备，ARP 表里可能查不到（`ip neigh` 只保留近期活跃项）。
- `oui.txt` 是静态快照，如需更新可重跑 `gen_oui_txt.py`（依赖同级的 `mac-lookup/oui-db.js`）。
- **流量统计**：`netmon-unified` 同时提供「累计字节」与「实时速率 ↓/↑」（基于 `/tmp/netmon_state.json` 两次采样差值）；`netmon-bandwidth.py N` 仍可做 N 秒独立采样。
- **App 分类基于端口**，无法识别同一端口下的不同 app（如 HTTPS/QUIC 可能对应微信、抖音、浏览器等不同应用）。
- **App 追踪基于 DNS**，仅在有 DNS 查询时生效；设备长时间未发起 DNS 请求则无记录。请在设备上打开对应 App 以触发 DNS 查询。
- 路由器未安装 `python3` 的设备不支持 `netmon-unified` 和 `netmon-bandwidth.py`（老版本 busybox 无 python）；此时只能用 `netmon-devices`（纯 shell + awk）。

## 重新打包 / 构建 .ipk

改了上面的脚本或页面后，重新生成安装包：

```sh
python3 build_ipk.py      # 生成 netmon_1.0.1-1_all.ipk
```

`build_ipk.py` 会把 `FILES` 列表里的源文件按路由器目标路径打进 `data.tar.gz`，并写入 `control.tar.gz`（含 `postinst`：安装后自动 `chmod +x` 并重启 uhttpd）。架构标记为 `all`（纯脚本/Lua/文本，无编译二进制，适配任意 CPU）。
