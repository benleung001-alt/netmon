# netmon-devices.awk —— 合并设备 + 输出 JSON
# 由 netmon-devices 调用：第一个文件是 OUI 查库结果（"OUI VENDOR"），
# 第二个文件是设备原始行（ip|mac|host|exp|src）。
#
# 兼容性注意：
#   变量名一律不靠大小写区分（部分 awk 大小写不敏感，且禁止同名标量/数组混用）。
#   U/L 位判定直接用 MAC 第二 hex 字符，避免依赖 strtonum/and（busybox awk 不一定有）。

function esc(s,   o, i, c) {
    o = ""
    for (i = 1; i <= length(s); i++) {
        c = substr(s, i, 1)
        if (c == "\\") o = o "\\\\"
        else if (c == "\"") o = o "\\\""
        else o = o c
    }
    return o
}

FNR == NR {
    key = $1
    $1 = ""
    vendor = $0
    sub(/^[ \t]+/, "", vendor)
    OUI[key] = vendor
    next
}

{
    n = split($0, a, "|")
    ip = a[1]; macv = a[2]; hostn = a[3]; expire = a[4]; srcc = a[5]
    if (ip == "") next
    if (!(ip in SEEN)) { SEEN[ip] = 1; order[++cnt] = ip }
    MACARR[ip] = macv
    if (hostn != "" && HOSTARR[ip] == "") HOSTARR[ip] = hostn
    if (expire != "") EXPARR[ip] = expire
    SRCARR[ip] = srcc
}

END {
    print "{"
    print "  \"generated\": " systime() ","
    print "  \"count\": " cnt ","
    print "  \"devices\": ["
    for (i = 1; i <= cnt; i++) {
        ip = order[i]; macv = MACARR[ip]; hostn = HOSTARR[ip]
        ouistr = toupper(macv); gsub(/[:-]/, "", ouistr); ouistr = substr(ouistr, 1, 6)
        c2 = substr(ouistr, 2, 1)
        if (c2 == "2" || c2 == "3" || c2 == "6" || c2 == "7" || c2 == "A" || c2 == "B" || c2 == "E" || c2 == "F") rnd = "true"
        else rnd = "false"
        if (rnd == "true") vendor = "私有地址(随机MAC)"
        else vendor = (ouistr in OUI) ? OUI[ouistr] : "未知"
        h = (hostn == "") ? "未知" : hostn
        printf "    {\"ip\":\"%s\",\"mac\":\"%s\",\"hostname\":\"%s\",\"vendor\":\"%s\",\"random_mac\":%s,\"expiry\":%s,\"source\":\"%s\"}%s\n",
            esc(ip), esc(macv), esc(h), esc(vendor), rnd, (EXPARR[ip] == "" ? "0" : EXPARR[ip]), srcc, (i < cnt ? "," : "")
    }
    print "  ]"
    print "}"
}
