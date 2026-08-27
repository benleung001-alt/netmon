#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 mac-lookup/oui-db.js 提取紧凑的 OUI->厂商 文本库，供 OpenWrt 路由器端
netmon-devices 脚本用 grep 快速查厂商。

输出格式（每行）：  OUI(大写6位) <空格> 厂商名
例：  9A216A Apple, Inc.
"""
import re
import os

SRC = os.path.join(os.path.dirname(__file__), "..", "mac-lookup", "oui-db.js")
DST_DIR = os.path.join(os.path.dirname(__file__), "usr", "share", "netmon")
DST = os.path.join(DST_DIR, "oui.txt")

os.makedirs(DST_DIR, exist_ok=True)

pat = re.compile(r'^\s*"([0-9A-Fa-f]{6})"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
count = 0
with open(SRC, "r", encoding="utf-8") as fin, open(DST, "w", encoding="utf-8") as fout:
    for line in fin:
        m = pat.match(line)
        if not m:
            continue
        oui = m.group(1).upper()
        vendor = m.group(2).replace('\\"', '"')
        fout.write(f"{oui} {vendor}\n")
        count += 1

print(f"written {count} OUI entries -> {os.path.abspath(DST)}")
