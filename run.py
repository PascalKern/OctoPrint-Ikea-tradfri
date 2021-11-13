#!/usr/bin/env python
import json
import uuid

from pytradfri.util import load_json, save_json
from pytradfri.const import ATTR_ID
from octoprint_ikea_tradfri_v2 import TradfriClient
from pytradfri.error import ServerError
from octoprint_ikea_tradfri_v2.tradfri_client import g_generate_psk

CONFIG = "run_conf.json"

# Note:
# When a identity is used to create a psk this psk can only be used TOGETHER with the
# generated identity!

args = {
    "gateway": "192.168.0.124",
    "security_code": "Nh1aEgM5okubRdRI",
    "identity": "my_tradfri_test",
}

cfg = load_json(CONFIG)

# Credits: https://stackoverflow.com/a/6159329
if cfg and all(x in cfg[args["gateway"]] for x in ["psk", "identity"]):
    psk = cfg[args["gateway"]]["psk"]
    print("Using existing psk from config json")
else:
    try:
        psk = TradfriClient.generate_psk(gateway=args["gateway"], identity=args["identity"],
                                         security_code=args["security_code"])
        print("Got initial PSK as: '%s'" % psk)
        save_json(CONFIG, {args["gateway"]: {"identity": args["identity"], "psk": psk}})
    except (KeyError, ServerError) as e:
        print("Seems something is wrong with the combination of identity (%s)" % args["identity"])
        print("with psk (%s) is not valid (anymore). Remove config for host: '%s' and retry!" % (psk, args["gateway"]))
        print("Error: %s", e)

client = TradfriClient(gw_ip=args["gateway"], identity=args["identity"], psk=psk)
print("Sockets are:")

for socket in client.get_sockets():
    print(socket)
    print(socket.raw)
    print(json.dumps(socket.raw, indent=2))
    print(socket.device_info.raw)
    print(socket.device_info.manufacturer)
    print("ID: '%s | %s', Name: '%s', Type: '%s'" % (socket.path, socket.raw.get(ATTR_ID), socket.name, 'Outlet'))
