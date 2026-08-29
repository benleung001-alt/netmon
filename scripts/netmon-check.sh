#!/bin/bash
# NetMon 自動核查腳本
# 用法：在任務完成後執行此腳本，或手動運行檢查

set -e
echo "=== NetMon 插件自動核查 $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""

ERRORS=0
WARNINGS=0

# 1. 檢查腳本文件存在性
echo "【1/6】檢查腳本文件..."
SCRIPTS=(
    "/usr/bin/netmon-unified"
    "/usr/bin/netmon-apptrace.py"
    "/usr/bin/netmon-report"
    "/usr/bin/netmon-mail-report"
    "/usr/share/netmon/config.json"
    "/usr/share/netmon/app_domains.json"
)

for f in "${SCRIPTS[@]}"; do
    if [ -f "$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ 缺失: $f"
        ERRORS=$((ERRORS + 1))
    fi
done

# 2. 檢查執行權限
echo ""
echo "【2/6】檢查執行權限..."
for f in /usr/bin/netmon-*; do
    if [ -x "$f" ]; then
        echo "  ✓ $(basename $f) 可執行"
    else
        echo "  ⚠ $(basename $f) 缺少執行權限"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# 3. Python 語法檢查
echo ""
echo "【3/6】Python 語法檢查..."
for py in /usr/bin/netmon-apptrace.py /usr/bin/netmon-report /usr/bin/netmon-mail-report; do
    if [ -f "$py" ]; then
        if python3 -m py_compile "$py" 2>/dev/null; then
            echo "  ✓ $(basename $py) 語法正確"
        else
            echo "  ✗ $(basename $py) 語法錯誤"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

# 4. 核心功能測試
echo ""
echo "【4/6】核心功能測試..."

# 測試 netmon-unified
if timeout 10 /usr/bin/netmon-unified > /dev/null 2>&1; then
    echo "  ✓ netmon-unified 運行正常"
else
    echo "  ⚠ netmon-unified 返回非零退出碼"
    WARNINGS=$((WARNINGS + 1))
fi

# 測試 netmon-apptrace.py
if timeout 10 /usr/bin/netmon-apptrace.py > /dev/null 2>&1; then
    echo "  ✓ netmon-apptrace.py 運行正常"
else
    echo "  ⚠ netmon-apptrace.py 返回非零退出碼"
    WARNINGS=$((WARNINGS + 1))
fi

# 5. 檢查 cron 定時任務
echo ""
echo "【5/6】檢查定時任務..."
if [ -f /etc/crontabs/root ]; then
    if grep -q "netmon" /etc/crontabs/root; then
        echo "  ✓ cron 任務已配置"
        grep "netmon" /etc/crontabs/root | while read line; do
            echo "    $line"
        done
    else
        echo "  ⚠ 未找到 netmon cron 任務"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠ cron 配置文件不存在"
    WARNINGS=$((WARNINGS + 1))
fi

# 檢查 cron 服務狀態
if pidof cron > /dev/null 2>&1; then
    echo "  ✓ cron 服務運行中"
else
    echo "  ⚠ cron 服務未運行"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. 檢查日誌錯誤
echo ""
echo "【6/6】檢查系統日誌..."
if logread -e "netmon" -l 100 2>/dev/null | grep -i "error\|fail\|exception" > /dev/null; then
    echo "  ⚠ 發現錯誤日誌："
    logread -e "netmon" -l 100 2>/dev/null | grep -i "error\|fail\|exception" | head -5 | while read line; do
        echo "    $line"
    done
    WARNINGS=$((WARNINGS + 1))
else
    echo "  ✓ 無錯誤日誌"
fi

# 總結
echo ""
echo "=== 核查結果 ==="
echo "錯誤: $ERRORS | 警告: $WARNINGS"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✓ 插件運行正常"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠ 插件基本正常，但有警告，請檢查上方輸出"
    exit 0
else
    echo "✗ 發現錯誤，請修復後重新部署"
    exit 1
fi
