#!/bin/bash
# NetMon 路由器诊断脚本
# 用法：ssh root@192.168.1.1 "bash -s" < diagnose-netmon.sh

echo "=== NetMon 诊断报告 ==="
echo "时间: $(date)"
echo ""

echo "【1. 检查已安装的NetMon版本】"
opkg list-installed | grep netmon || echo "未找到netmon包"
echo ""

echo "【2. 检查模板文件是否存在及内容】"
if [ -f "/usr/lib/lua/luci/view/netmon/devices.htm" ]; then
    echo "✓ 模板文件存在"
    echo "  文件大小: $(wc -c < /usr/lib/lua/luci/view/netmon/devices.htm) bytes"
    echo "  最后修改: $(stat -c %y /usr/lib/lua/luci/view/netmon/devices.htm 2>/dev/null || echo '未知')"
    
    # 检查关键函数
    if grep -q "local function fmt_rate" /usr/lib/lua/luci/view/netmon/devices.htm; then
        echo "✓ 找到 fmt_rate 函数"
        echo "  当前实现:"
        grep -A 7 "local function fmt_rate" /usr/lib/lua/luci/view/netmon/devices.htm | head -8
    else
        echo "✗ 未找到 fmt_rate 函数！"
    fi
    
    # 检查所有string.format调用
    echo ""
    echo "  所有string.format调用:"
    grep -n "string.format" /usr/lib/lua/luci/view/netmon/devices.htm
else
    echo "✗ 模板文件不存在！"
fi
echo ""

echo "【3. 检查LuCI缓存】"
if [ -d "/tmp/luci-cache" ]; then
    echo "LuCI缓存目录: /tmp/luci-cache"
    ls -la /tmp/luci-cache/ 2>/dev/null | head -10
else
    echo "未找到LuCI缓存目录"
fi
echo ""

echo "【4. 检查核心脚本】"
for script in netmon-unified netmon-apptrace.py netmon-bandwidth.py; do
    if [ -f "/usr/bin/$script" ]; then
        echo "✓ /usr/bin/$script 存在 ($(wc -c < /usr/bin/$script) bytes)"
    else
        echo "✗ /usr/bin/$script 不存在"
    fi
done
echo ""

echo "【5. 测试netmon-unified脚本】"
if [ -x "/usr/bin/netmon-unified" ]; then
    timeout 5 /usr/bin/netmon-unified 2>/tmp/netmon-error.log | head -20
    if [ $? -ne 0 ]; then
        echo "✗ 脚本执行失败"
        echo "错误日志:"
        cat /tmp/netmon-error.log 2>/dev/null
    else
        echo "✓ 脚本执行成功"
    fi
else
    echo "✗ netmon-unified 不可执行"
fi
echo ""

echo "【6. 检查系统日志】"
echo "最近的netmon相关错误:"
logread 2>/dev/null | grep -i "netmon\|format\|error" | tail -10 || echo "无法读取日志"
echo ""

echo "【7. 检查LuCI服务状态】"
/etc/init.d/uhttpd status 2>/dev/null && echo "✓ uhttpd 运行中" || echo "✗ uhttpd 未运行"
echo ""

echo "【8. 建议操作】"
echo "如果发现问题，请按以下顺序执行："
echo "1. 重新安装IPK: opkg install /tmp/netmon_x.x.x-1_all.ipk --force-reinstall"
echo "2. 清除LuCI缓存: rm -rf /tmp/luci-*"
echo "3. 重启Web服务: /etc/init.d/uhttpd restart"
echo "4. 如果仍有问题，重启路由器"
echo ""

echo "=== 诊断完成 ==="
