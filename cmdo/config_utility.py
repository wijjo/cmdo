#===============================================================================
#===============================================================================
# Config file support
#
# Author Steve Cooper   steve@wijjo.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#===============================================================================
#===============================================================================

import os.path
import ConfigParser

#===============================================================================

class Config(object):

    # Force option names to maintain their case
    class Parser(ConfigParser.ConfigParser):
        def __init__(self, caseSensitive):
            self.caseSensitive = caseSensitive
            ConfigParser.ConfigParser.__init__(self)
        def optionxform(self, name):
            if self.caseSensitive:
                return name
            return name.lower()

    def __init__(self, name, home, extConfig, caseSensitive):
        self.path = os.path.join(home, '%s%s' % (name, extConfig))
        self.parser = None
        self.caseSensitive = caseSensitive

    def initialize(self):
        if not self.parser:
            self.parser = Config.Parser(self.caseSensitive)
            if os.path.exists(self.path):
                fp = open(self.path)
                try:
                    self.parser.readfp(fp, self.path)
                finally:
                    fp.close()

    def set(self, section, name, value):
        self.initialize()
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, name, str(value))

    def get(self, section, name, default = None):
        self.initialize()
        try:
            return self.parser.get(section, name)
        except:
            return default

    def getInteger(self, section, name, default = 0):
        self.initialize()
        try:
            return int(self.parser.get(section, name))
        except:
            return default

    def getSection(self, section):
        self.initialize()
        try:
            d = {}
            for (name, value) in self.parser.items(section):
                d[name] = value
            return d
        except:
            return {}

    def getSectionSorted(self, section):
        self.initialize()
        d = self.getSection(section)
        keys = d.keys()
        keys.sort()
        items = []
        for key in keys:
            items.append((key, d[key]))
        return items

    def removeSection(self, section):
        self.initialize()
        if self.parser.has_section(section):
            self.parser.remove_section(section)

    def remove(self, section, name):
        self.initialize()
        if self.parser.has_section(section) and self.parser.has_option(section, name):
            self.parser.remove_option(section.name)

    def getSectionNames(self):
        self.initialize()
        names = self.parser.sections()
        names.sort()
        return names

    def save(self):
        self.initialize()
        fp = open(self.path, 'w')
        try:
            self.parser.write(fp)
        finally:
            fp.close()

#===============================================================================

class ConfigFactory(object):
    def __init__(self, home, ext):
        self.home = home
        self.ext  = ext
    def config(self, name, caseSensitive = False):
        return Config(name, self.home, self.ext, caseSensitive)
