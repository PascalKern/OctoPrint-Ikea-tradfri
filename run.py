#!/usr/bin/env python

import json

from octoprint_ikea_tradfri_v2 import TradfriClient

client = TradfriClient("192.168.0.124", "Nh1aEgM5okubRdRI")
print("Sockets are:")
for socket in client.get_sockets():
    print(socket)
    print(json.dumps(socket.raw, indent=2))

# print("Devices are:")
# for dev in client.list_devices():
#     print(dev)
