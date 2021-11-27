import json
import uuid
import flask
import logging

from pytradfri.error import PytradfriError

import octoprint
from octoprint.plugin import WizardPlugin, SettingsPlugin

from octoprint_ikea_tradfri_v2.tradfri_client import TradfriClient, generate_psk


def get_user_id():
    return "OctoPrintTradfriV2Plugin-%s" % uuid.uuid4().hex[:6]


class IkeaTradfriPluginWizard(
    WizardPlugin,
    SettingsPlugin
):

    def is_wizard_required(self):
        gateway_ip = self._settings.get(["gateway_ip"])
        psk = self._settings.get(["psk"])
        identity = self._settings.get(["identity"])
        self._logger.debug("Check if wizard is required?")
        is_required = gateway_ip == "" or psk == "" or identity == ""
        self._logger.debug("IP: '%s', PSK: '%s' and Identity: '%s' -> Required: '%s'" % (gateway_ip, psk, identity, is_required))
        return is_required

    def get_wizard_version(self):
        return 2

    @octoprint.plugin.BlueprintPlugin.route("/wizard/setOutlet", methods=["POST"])
    def wizard_set_outlet(self):
        if "selected_outlet" not in flask.request.json:
            return flask.make_response("Expected selected_outlet.", 400)
        selected_outlet = flask.request.json['selected_outlet']

        dev = dict(
            name="Printer",
            id=selected_outlet,
            type="Outlet",
            connection_timer=5,
            stop_timer=30,
            postpone_delay=30,
            turn_off_mode="cooldown",
            cooldown_bed=-1,
            cooldown_hotend=50,
            on_done=True,
            on_failed=False,
            icon="plug",
            nav_name=False,
            nav_icon=True
        )
        self._settings.set(['selected_devices'], [dev])
        self._settings.save()

        return flask.make_response("OK", 200)

    @octoprint.plugin.BlueprintPlugin.route("/wizard/tryConnect", methods=["POST"])
    def wizard_try_connect(self):
        if "securityCode" not in flask.request.json or "gateway" not in flask.request.json:
            return flask.make_response("Expected security code and gateway.", 400)

        gateway = flask.request.json['gateway']
        security_code = flask.request.json['securityCode']
        self._logger.info("TryConnect got security-code: '%s' and gateway: '%s'" % (security_code, gateway))

        identity = get_user_id()

        try:
            psk = generate_psk(gateway=gateway, identity=identity, security_code=security_code)
        except PytradfriError as e:
            self._logger.error("Wizard : Error on creating psk!", e)
            return flask.make_response("Failed generate psk. Error: %s" % e.__repr__(), 500)

        if psk is not None:
            self._settings.set(['identity'], identity)
            self._settings.set(['psk'], psk)
            self._settings.set(['gateway_ip'], gateway)
            self._settings.save()

            devices = TradfriClient.setup(gw_ip=gateway, identity=identity, psk=psk).list_devices()

            if devices:
                self._logger.debug(f"Seem to got some devices. Going to save them now. Data: '{devices}'")
                self._settings.set(['devices'], [dev.to_dict() for dev in devices])
                self._settings.save()
                return flask.make_response(json.dumps([dev.to_dict() for dev in devices], indent=4), 200)
            return flask.make_response(json.dumps("{}"), 200)
        else:
            self._logger.error('Failed to get psk key (wizard_try_connect)')
            return flask.make_response("Failed to connect.", 500)

    def on_wizard_finish(self, handled):
        self._logger.info("Wizard finished! Handled: '%s'" % handled)
        pass

    @classmethod
    def is_wizard_ignored(cls, seen_wizards, implementation):
        logging.getLogger(__name__).debug("Wizard is ignored (ie. return False). Seen: '%s', implementation: '%s'"
                                          % (seen_wizards, implementation))
        return False  # Only while developing!
