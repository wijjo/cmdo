#===============================================================================
#===============================================================================
# Cmdo - public symbols
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

from sys import maxint

import re

# Pass most of the utility stuff
# They're kept separate so that they can be used on their own, e.g. if doc.py
# is used independently.
from log_utility import *
from sys_utility import *
from text_utility import *

# Manage creation of Config objects here to pass in program.home.
import config_utility

# File extension constants
extConfig = '.conf'
extModule = '.cmdo'
extCore   = '.cmdocore'
extDoc    = '.cmdodoc'

# Populated during startup
program    = None
engine     = None
verbose    = False
debug      = False
publishers = {}
guis       = {}

# Created on first use
_configFactory = None

# Extra documentation for variables
_symsDoc = {
    'program'    : 'Application object',
    'engine'     : 'Engine object',
    'verbose'    : 'Display verbose messages if True',
    'debug'      : 'Display debugging messages if True',
    'publishers' : 'Dictionary of available formats/publishers',
    'guis'       : 'Dictionary of available GUIs',
    'extConfig'  : 'Configuration file extension, including leading "."',
    'extCore'    : 'Core module file extension, including leading "."',
    'extModule'  : 'Module file extension, including leading "."',
    'extDoc'     : 'Documentation module file extension, including leading "."',
}

reSym   = re.compile('^[a-z_][a-z0-9_.]*$', re.IGNORECASE)
reKwarg = re.compile('^([a-z_][a-z0-9_]*)[ \t]*=[ \t]*(.*)[ \t]*$', re.IGNORECASE)
reNum   = re.compile('^[+-]?[0-9.]+$')

#===============================================================================
# Publisher registry - allows extension and customization of built-in support.
#===============================================================================

def registerPublisher(name, cls):
    '''Register documentation publisher name and class.'''
    global publishers
    publishers[name] = cls

#===============================================================================
# GUI registry - plug-in's providing different prompting GUIs.
#===============================================================================

def registerGUI(name, cls):
    '''Register GUI name and class.'''
    global guis
    guis[name] = cls

#===============================================================================

# Inherit from this to mark classes in type files for export
class ExportedClass:
    '''Base class for classes exported from module files'''
    pass

#===============================================================================

class ExcBase(Exception):
    '''Base exception class'''
    def __init__(self, *args):
        self.traceback = False
        for arg in args:
            if isinstance(arg, Exception):
                if not isinstance(arg, ExcBase) or arg.traceback:
                    self.traceback = True
                    break
        self.s = '\n'.join([str(arg) for arg in args])
    def __str__(self):
        return self.s
class ExcConversion(ExcBase):
    '''Argument conversion exception'''
    pass
class ExcFunction(ExcBase):
    '''Exported function exception'''
    pass
class ExcArgument(ExcBase):
    '''Argument processing exception'''
    pass
class ExcPath(ExcBase):
    '''File or directory exception'''
    pass
class ExcFile(ExcBase):
    '''File input/output exception'''
    pass
class ExcDoc(ExcBase):
    '''Documentation exception'''
    pass
class ExcLoad(ExcBase):
    '''Load-time exception'''
    pass

#===============================================================================

class TypeBase(object):
    '''Base argument type class'''
    def __init__(self, desc = 'generic argument', valueDef = None, descDef = None):
        self.desc     = desc
        self.descDef  = descDef
        self.valueDef = valueDef
        if self.desc is None:
            self.desc = self.__class__.__name__
        if self.descDef is None and self.valueDef is not None:
            self.descDef = str(self.valueDef)
    # Generally not overridden if convert() is provided
    def get(self, value):
        if value is None:
            value = self.getDefault()
        if value is not None:
            value = self.convert(value)
        return value
    # Override for custom conversions
    def convert(self, value):
        return value
    def getDefault(self):
        return self.valueDef
    def hasDefault(self):
        return self.getDefault() is not None

#===============================================================================

class More(TypeBase):
    '''Special type for accepting a variable quantity of additional arguments.
    Optional arguments specify a validation type ("type"), a minimum quantity
    ("countMin"), a maximum quantity ("countMax"), and a description
    ("desc").'''
    def __init__(self,
            type     = None,
            countMin = 0,
            countMax = sys.maxint,
            desc     = None):
        self.type     = None
        self.countMin = countMin
        self.countMax = countMax
        import inspect
        if isinstance(type, TypeBase):
            self.type = type
        elif inspect.isclass(type) and issubclass(type, TypeBase):
            try:
                self.type = type()
            except:
                pass
        if type and not self.type:
            raise ExcArgument('Bad type definition (%s) in More' % str(type))
        if not desc:
            if self.countMax == sys.maxint:
                desc = '%d-n of: ' % self.countMin
            else:
                desc = '%d-%s of: ' % (self.countMin, self.countMax)
            if self.type:
                desc += self.type.desc
            else:
                desc += 'generic arguments'
        TypeBase.__init__(self, desc)
    def convert(self, value):
        if self.type:
            return self.type.convert(value)
        return value

#===============================================================================

def config(name, caseSensitive = False):
    '''Returns a configuration object for accessing a configuration file in the
    application home directory.'''
    global _configFactory
    if _configFactory is None:
        _configFactory = config_utility.ConfigFactory(program.home, extConfig)
    return _configFactory.config(name, caseSensitive = caseSensitive)

#===============================================================================

def docParseString(s):
    '''Parses structured text documentation in a string and returns the root node.'''
    from cmdo import doc
    try:
        doc.parserStrucText.parse(s)
        return doc.parserStrucText.take()
    except Exception, e:
        error('Unable to parse documentation string', str(e))
        return None

#===============================================================================

def docParse(path):
    '''Parses structured text documentation in a file and returns the root node.'''
    from cmdo import doc
    try:
        doc.parserStrucText.parse(open(path).read())
        return doc.parserStrucText.take()
    except Exception, e:
        error('Unable to access documentation in "%s"' % path, str(e))
        return None

#===============================================================================

def _getArgsCommands(args):
    '''Analyzes command arguments.  If it looks like simplified command syntax
    builds a single good command.  Otherwise just returns the arguments
    unchanged.'''
    if not args:
        return []
    # Assume a simplified command line if the first argument is a plain symbol
    if not reSym.match(args[0]):
        return args
    argsIn = []
    kwargsIn = []
    for argIn in args[1:]:
        m = reKwarg.match(argIn)
        if m is not None:
            prefix= '%s=' % m.group(1)
            v = m.group(2)
        else:
            prefix = ''
            v = argIn
        if not reNum.match(v):
            #TODO: Escape imbedded quotes
            v = '"%s"' % v
        if prefix:
            kwargsIn.append('%s%s' % (prefix, v))
        else:
            argsIn.append(v)
    body = ','.join(argsIn + kwargsIn)
    cmd  = '%s(%s)' % (args[0], body)
    if verbose:
        info('simple command: "%s"' % cmd)
    return [cmd]

#===============================================================================

def _getStringCommands(s):
    '''Analyzes a command string and extracts one or more commands, depending
    on whether or not simplified syntax is used.  Uses shell parsing to deal
    with quotes, etc.'''
    import shlex
    return _getArgsCommands(shlex.split(s))

#===============================================================================

def execute(s):
    '''Executes a string as one or more commands by using smart command parsing
    to detect and handle simplified syntax, if used.'''
    if verbose:
        info('Execute: %s' % s)
    for sCmd in _getStringCommands(s):
        exec sCmd in program.symsExec

#===============================================================================

def getFunction(s):
    '''Converts function name to Function object.'''
    return program.exports.getModuleFunction(s)[1]

#===============================================================================

def getModuleFunction(s):
    '''Converts module and or function names to Module/Function pair.  Either
    or both may be returned as None.'''
    return program.exports.getModuleFunction(s)
