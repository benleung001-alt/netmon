-- LuCI 控制器：在「状态」菜单下挂载 NetMon 设备清单页
module("luci.controller.netmon", package.seeall)

function index()
    entry({"admin", "status", "netmon"},
          template("netmon/devices"),
          _("NetMon 设备清单"),
          60)
end
