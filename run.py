#!/usr/bin/env python
import asyncio
import json
import uuid

from pytradfri.const import ATTR_ID
from octoprint_ikea_tradfri_v2 import TradfriClient
from octoprint_ikea_tradfri_v2.tradfri_client import g_generate_psk

# Note:
# When a identity is used to create a psk this psk can only be used TOGETHER with the
# generated identity!

args = {
    "gateway": "192.168.0.124",
    "security_code": "Nh1aEgM5okubRdRI",
    # "identity": "my_pytradfri_test",                          # Not working!!
    "identity1": "50cfa8b5-f2b7-4ca0-ac49-3deae549ed23",  # uuid.uuid4()
    # "identity1.1": "68a9da94c0c949be8c517868595c37db",  # uuid.uuid4().hex
    "identity1.1": uuid.uuid4().hex,  # Use as long as psk is not proper saved and reused between runs (the Gateway does remember the id and check against the psk!)
    "identity1.2": "6d795f7079747261646672695f74657374",  # "my_pytradfri_test".encode().hex()
}

args2 = {
    "gateway": "192.168.0.124",
    "security_code": "Nh1aEgM5okubRdRI",
    "identity": "68a9da94c0c949be8c517868595c37db",  # uuid.uuid4().hex
}

psk = TradfriClient.generate_psk(gateway=args["gateway"], identity=args["identity1.1"],
                                 security_code=args["security_code"])

# psk = asyncio.get_event_loop().run_until_complete(
#     g_generate_psk(gateway=args["gateway"], identity=args["identity1.1"], security_code=args["security_code"])
# )

# psk = TradfriClient.generate_psk(**args2)
print("Got initial PSK as: '%s'" % psk)

# Can not re-use this methode as the api_factory.init does not use the psk - as it is anyway not needed!
# psk = TradfriClient.generate_psk(gateway=args["gateway"], identity=args["identity1.1"],
#                                  security_code=psk)
# print("Got PSK as: '%s'" % psk)


client = TradfriClient(gw_ip=args["gateway"], identity=args["identity1.1"], psk=psk)
print("Sockets are:")

for socket in client.get_sockets():
    print(socket)
    print(socket.raw)
    print(json.dumps(socket.raw, indent=2))
    print(socket.device_info.raw)
    print(socket.device_info.manufacturer)
    print("ID: '%s | %s', Name: '%s', Type: '%s'" % (socket.path, socket.raw.get(ATTR_ID), socket.name, 'Outlet'))
