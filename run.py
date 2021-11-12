#!/usr/bin/env python

import json
from pytradfri.const import ATTR_ID
from octoprint_ikea_tradfri_v2 import TradfriClient

client = TradfriClient(gw_ip="192.168.0.124", gw_sec_key="Nh1aEgM5okubRdRI")
print("Sockets are:")
for socket in client.get_sockets():
    print(socket)
    print(socket.raw)
    print(json.dumps(socket.raw, indent=2))
    print(socket.device_info.raw)
    print(socket.device_info.manufacturer)
    print("ID: '%s | %s', Name: '%s', Type: '%s'" % (socket.path, socket.raw.get(ATTR_ID), socket.name, 'Outlet'))

# print("Devices are:")
# for dev in client.list_devices():
#     print(dev)
