#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 netmon 模块打包成标准 OpenWrt .ipk 安装包。

.ipk 本质是 ar 归档，内含：
  debian-binary  -> "2.0"
  control.tar.gz -> ./control + ./postinst
  data.tar.gz    -> 部署到路由器的文件（按目标绝对路径，去掉开头的 /）

用法（在本目录执行）：
  python3 build_ipk.py
生成：netmon_1.0.0-1_all.ipk
"""
import os
import gzip
import tarfile
import struct
import io

OUT_IPK = "netmon_1.0.16-1_all.ipk"
PKG_DIR = os.path.dirname(os.path.abspath(__file__))

# 源文件 -> 路由器目标路径（去掉开头的 /）
FILES = [
    ("usr/bin/netmon-devices",                 "usr/bin/netmon-devices",                 0o0755),
    ("usr/bin/netmon-devices.awk",             "usr/bin/netmon-devices.awk",            0o0644),
    ("usr/bin/netmon-unified",                 "usr/bin/netmon-unified",                0o0755),
    ("usr/bin/netmon-bandwidth.py",            "usr/bin/netmon-bandwidth.py",           0o0755),
    ("usr/bin/netmon-apptrace.py",             "usr/bin/netmon-apptrace.py",            0o0755),
    ("usr/bin/netmon-report",                   "usr/bin/netmon-report",                 0o0755),
    ("usr/bin/netmon-mail-report",              "usr/bin/netmon-mail-report",            0o0755),
    ("etc/netmon-mail.conf",                    "etc/netmon-mail.conf",                  0o0600),
    ("usr/share/netmon/oui.txt",               "usr/share/netmon/oui.txt",              0o0644),
    ("usr/lib/lua/luci/controller/netmon.lua", "usr/lib/lua/luci/controller/netmon.lua",0o0644),
    ("usr/lib/lua/luci/view/netmon/devices.htm","usr/lib/lua/luci/view/netmon/devices.htm",0o0644),
    ("scripts/netmon-check.sh",                "usr/bin/netmon-check",                   0o0755),
    ("scripts/diagnose-netmon.sh",             "usr/bin/diagnose-netmon",                0o0755),
]

CONTROL = """Package: netmon
Version: 1.0.16-1
Section: net
Priority: optional
Architecture: all
Maintainer: ben <ben@local>
Source: netmon
Depends: luci-base, cron
Description: DHCP device list with hostname / vendor / random-MAC detection + 40+ App tracing (抖音/快手/B站/微信/微软/WPS等) + daily report (JSON/MD/HTML) + styled HTML email delivery + search/sort/filter UI for OpenWrt routers.
"""

POSTINST = """#!/bin/sh
# 安装后赋予脚本执行权限并刷新 LuCI 让菜单生效
chmod 0755 /usr/bin/netmon-devices /usr/bin/netmon-unified /usr/bin/netmon-bandwidth.py /usr/bin/netmon-apptrace.py /usr/bin/netmon-report /usr/bin/netmon-mail-report /usr/bin/netmon-check 2>/dev/null
chmod 0600 /etc/netmon-mail.conf 2>/dev/null
/etc/init.d/uhttpd restart 2>/dev/null
# 配置每日采集+cron（每天 23:30，生成报告并邮件发送），仅追加一次，不覆盖用户其它任务
mkdir -p /etc/netmon-reports
if ! grep -q "netmon-mail-report" /etc/crontabs/root 2>/dev/null; then
  echo "30 23 * * * /usr/bin/netmon-mail-report >> /etc/netmon-reports/cron.log 2>&1" >> /etc/crontabs/root
  chmod 600 /etc/crontabs/root 2>/dev/null
  /etc/init.d/cron restart 2>/dev/null
fi
exit 0
"""


def make_tar_gz(paths_and_modes, base_dir):
    """paths_and_modes: list of (rel_src, tar_name, mode). 返回 gz 字节。"""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for src_rel, tar_name, mode in paths_and_modes:
                src = os.path.join(base_dir, src_rel)
                ti = tarfile.TarInfo(name=tar_name)
                with open(src, "rb") as f:
                    data = f.read()
                ti.size = len(data)
                ti.mode = mode
                ti.mtime = 0
                ti.type = tarfile.REGTYPE
                tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def ar_append(members):
    """members: list of (name:str, data:bytes). 返回完整 ar 字节。"""
    out = bytearray(b"!<arch>\n")
    for name, data in members:
        # 名字固定 16 字节，不足空格补齐；目录用 "/" 结尾（这里文件不用）
        nm = name.encode("ascii")
        if len(nm) > 16:
            nm = nm[:16]
        name_field = nm + b" " * (16 - len(nm))
        size = len(data)
        header = struct.pack(
            "16s12s6s6s8s10s2s",
            name_field,
            b"0" * 12,        # mtime
            b"0" * 6,         # uid
            b"0" * 6,         # gid
            b"100644 ",       # mode (含尾空格)
            ("%10d" % size).encode(),  # size 10 位
            b"`\n",           # 结束符
        )
        assert len(header) == 60, len(header)
        out += header
        out += data
        if size % 2 == 1:          # ar 要求偶数对齐
            out += b"\n"
    return bytes(out)


def main():
    base = PKG_DIR
    # 1) data.tar.gz
    data_tar = make_tar_gz([(s, t, m) for (s, t, m) in FILES], base)

    # 2) control.tar.gz
    ctrl_members = [("control", CONTROL.encode("utf-8")),
                    ("postinst", POSTINST.encode("utf-8"))]
    ctrl_buf = io.BytesIO()
    with gzip.GzipFile(fileobj=ctrl_buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for nm, content in ctrl_members:
                ti = tarfile.TarInfo(name=nm)
                ti.size = len(content)
                ti.mode = 0o0644
                ti.mtime = 0
                if nm == "postinst":
                    ti.mode = 0o0755
                ti.type = tarfile.REGTYPE
                tar.addfile(ti, io.BytesIO(content))
    ctrl_tar = ctrl_buf.getvalue()

    # 3) debian-binary
    debian = b"2.0\n"

    # 4) 组装 ar
    ar_bytes = ar_append([
        ("debian-binary", debian),
        ("control.tar.gz", ctrl_tar),
        ("data.tar.gz", data_tar),
    ])

    out_path = os.path.join(base, OUT_IPK)
    with open(out_path, "wb") as f:
        f.write(ar_bytes)
    print("已生成:", out_path, "(%d bytes)" % len(ar_bytes))


if __name__ == "__main__":
    main()
