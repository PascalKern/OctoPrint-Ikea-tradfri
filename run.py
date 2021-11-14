#!/usr/bin/env python
import json

from pytradfri.util import load_json, save_json
from pytradfri.const import ATTR_ID
from octoprint_ikea_tradfri_v2 import TradfriClient
from pytradfri.error import ServerError

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
        print("=" * 96)
        save_json(CONFIG, {args["gateway"]: {"identity": args["identity"], "psk": psk}})
    except (TypeError, ServerError) as e:
        print("    Error: %s" % e)
        print("=" * 96)
        print("    Seems something is wrong with the combination of identity (%s)" % args["identity"])
        if 'psk' in locals():
            print("    with psk (%s) is not valid (anymore). Remove config for host: '%s' and retry!" % (psk, args["gateway"]))
        else:
            print("    with psk (%s) is not valid (anymore). Remove config for host: '%s' and retry!" % ('psk undefined', args["gateway"]))
        print("    IMPORTANT: Most likely you must change the identity too!")
        print("=" * 96)
        exit(1)

client = TradfriClient(gw_ip=args["gateway"], identity=args["identity"], psk=psk)
print("=" * 96)
print("Sockets (and infos) are:")
for socket in client.get_sockets():
    print("-" * 10)
    print(socket)
    print("-" * 10)
    print(socket.raw)
    print("-" * 10)
    print(json.dumps(socket.raw, indent=2))
    print("-" * 10)
    print(socket.device_info.raw)
    print("-" * 10)
    print(socket.device_info.manufacturer)
    print("-" * 10)
    print("ID: '%s | %s', Name: '%s', Type: '%s'" % (socket.path, socket.raw.get(ATTR_ID), socket.name, 'Outlet'))
print("=" * 96)
