# -*- coding: utf-8 -*-
from . import cli
from octoprint_ikea_tradfri_v2.octoprint_ikea_tradfri_v2_plugin import IkeaTradfriPlugin

global __plugin_hooks__
global __plugin_implementation__


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "OctoPrint Ikea Tradfri v2"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = IkeaTradfriPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.cli.commands": cli.commands,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.access.permissions": __plugin_implementation__.get_additional_permissions
    }
