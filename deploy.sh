#!/usr/bin/env bash
# =====================================================================
#  deploy.sh —— 一键把 NetMon 上传到 OpenWrt 路由器（Cudy TR3000 等）
#
#  用法（在能连路由器的电脑 / 同一局域网的终端里运行）：
#    ./deploy.sh                 # 用默认 192.168.1.1 / root
#    ROUTER_HOST=192.168.0.1 ./deploy.sh
#    ROUTER_HOST=192.168.1.1 ROUTER_USER=root ./deploy.sh
#
#  前置：本机已装 OpenSSH（ssh / scp）。Windows 用 Git Bash 或 WSL 运行。
#  认证：脚本用你本机已有的 SSH 密钥或交互输密码，无需在此填密码。
#  若路由器未开启 SSH / 只用 LuCI 网页，请用同目录的 netmon_*.ipk 上传安装。
# =====================================================================
set -euo pipefail

ROUTER_HOST="${ROUTER_HOST:-192.168.1.1}"
ROUTER_PORT="${ROUTER_PORT:-22}"
ROUTER_USER="${ROUTER_USER:-root}"

BASE="$(cd "$(dirname "$0")" && pwd)"

echo "==> 目标路由器: ${ROUTER_USER}@${ROUTER_HOST}:${ROUTER_PORT}"

# ---- 1. 上传文件 ----
echo "==> [1/3] 上传文件 ..."
scp -P "$ROUTER_PORT" \
    "$BASE/usr/bin/netmon-devices" \
    "$BASE/usr/bin/netmon-devices.awk" \
    "${ROUTER_USER}@${ROUTER_HOST}:/usr/bin/" 2>&1

ssh -p "$ROUTER_PORT" "${ROUTER_USER}@${ROUTER_HOST}" "mkdir -p /usr/share/netmon /usr/lib/lua/luci/view/netmon"

scp -P "$ROUTER_PORT" \
    "$BASE/usr/share/netmon/oui.txt" \
    "${ROUTER_USER}@${ROUTER_HOST}:/usr/share/netmon/" 2>&1

scp -P "$ROUTER_PORT" \
    "$BASE/usr/lib/lua/luci/controller/netmon.lua" \
    "${ROUTER_USER}@${ROUTER_HOST}:/usr/lib/lua/luci/controller/" 2>&1

scp -P "$ROUTER_PORT" \
    "$BASE/usr/lib/lua/luci/view/netmon/devices.htm" \
    "${ROUTER_USER}@${ROUTER_HOST}:/usr/lib/lua/luci/view/netmon/" 2>&1

# ---- 2. 赋权 + 刷新 LuCI ----
echo "==> [2/3] 赋执行权限 + 重启 uhttpd ..."
ssh -p "$ROUTER_PORT" "${ROUTER_USER}@${ROUTER_HOST}" \
    "chmod 0755 /usr/bin/netmon-devices; /etc/init.d/uhttpd restart" 2>&1

# ---- 3. 验证 ----
echo "==> [3/3] 运行 netmon-devices 验证 ..."
ssh -p "$ROUTER_PORT" "${ROUTER_USER}@${ROUTER_HOST}" \
    "/usr/bin/netmon-devices 2>/dev/null | head -c 400; echo" 2>&1

echo
echo "✅ 完成！登录路由器 LuCI → 状态 → NetMon 设备清单 查看。"
