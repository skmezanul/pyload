#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from new_collections import OrderedDict

from pyload.Api import InvalidConfigSection
from pyload.utils import json

from .ConfigParser import ConfigParser

from .convert import to_input, from_string

def convertKeyError(func):
    """ converts KeyError into InvalidConfigSection """

    def conv(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            raise InvalidConfigSection(args[1])

    return conv


class ConfigManager(ConfigParser):
    """ Manages the core config and configs for addons and single user.
        Has similar interface to ConfigParser. """

    def __init__(self, core, parser):
        # No __init__ call to super class is needed!

        self.core = core
        self.db = core.db
        # The config parser, holding the core config
        self.parser = parser

        # similar to parser, separated meta data and values
        self.config = OrderedDict()

        # Value cache for multiple user configs
        # Values are populated from db on first access
        # Entries are saved as (user, section) keys
        self.values = {}
        # TODO: similar to a cache, could be deleted periodically

    def save(self):
        self.parser.save()

    @convertKeyError
    def get(self, section, option, user=None):
        """get config value, core config only available for admins.
        if user is not valid default value will be returned"""

        # Core config loaded from parser, when no user is given or he is admin
        if section in self.parser and user is None:
            return self.parser.get(section, option)
        else:
            # We need the id and not the instance
            # Will be None for admin user and so the same as internal access
            try:
                # Check if this config exists
                # Configs without meta data can not be loaded!
                data = self.config[section].config[option]
                return self.loadValues(user, section)[option]
            except KeyError:
                pass # Returns default value later

        return self.config[section].config[option].input.default_value

    def loadValues(self, user, section):
        if (user, section) not in self.values:
            conf = self.db.loadConfig(section, user)
            try:
                self.values[user, section] = json.loads(conf) if conf else {}
            except ValueError: # Something did go wrong when parsing
                self.values[user, section] = {}
                self.core.print_exc()

        return self.values[user, section]

    @convertKeyError
    def set(self, section, option, value, sync=True, user=None):
        """ set config value  """

        changed = False
        if section in self.parser and user is None:
            changed = self.parser.set(section, option, value, sync)
        else:
            data = self.config[section].config[option]
            value = from_string(value, data.input.type)
            old_value = self.get(section, option)

            # Values will always be saved to db, sync is ignored
            if value != old_value:
                changed = True
                self.values[user, section][option] = value
                if sync: self.saveValues(user, section)

        if changed: self.core.evm.dispatchEvent("config:changed", section, option, value)
        return changed

    def saveValues(self, user, section):
        if section in self.parser and user is None:
            self.save()
        elif (user, section) in self.values:
            self.db.saveConfig(section, json.dumps(self.values[user, section]), user)

    def delete(self, section, user=None):
        """ Deletes values saved in db and cached values for given user, NOT meta data
            Does not trigger an error when nothing was deleted. """
        if (user, section) in self.values:
            del self.values[user, section]

        self.db.deleteConfig(section, user)
        self.core.evm.dispatchEvent("config:deleted", section, user)

    def iterCoreSections(self):
        return self.parser.iterSections()

    def iterSections(self, user=None):
        """ Yields: section, metadata, values """
        values = self.db.loadConfigsForUser(user)

        # Every section needs to be json decoded
        for section, data in values.items():
            try:
                values[section] = json.loads(data) if data else {}
            except ValueError:
                values[section] = {}
                self.core.print_exc()

        for name, config in self.config.items():
            yield name, config, values[name] if name in values else {}

    def getSection(self, section, user=None):
        if section in self.parser and user is None:
            return self.parser.getSection(section)

        values = self.loadValues(user, section)
        return self.config.get(section), values
