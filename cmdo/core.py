#===============================================================================
#===============================================================================
# Cmdo - engine
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

import sys
import os.path
import glob
import imp
import inspect
import re
import types
import copy
from cmdo import public, doc, structext
from cmdo import publish_text, publish_html, publish_xml
from cmdo import ui_text
from cmdo import log_utility, text_utility

versionEng = '0.8'

decorators = ['export', 'internal', 'document']

duplicateFunctions  = []

exportedClasses = [public.TypeBase, public.ExcBase, public.ExportedClass]

symsCore = {}

public.registerPublisher('text', publish_text.Publisher)
public.registerPublisher('html', publish_html.Publisher)
public.registerPublisher('xml',  publish_xml .Publisher)

public.registerGUI('text', ui_text.Driver)

loadedCoreDocumentation = False

#===============================================================================

class ExportedModule(object):

    def __init__(self, name, path):
        self._name      = name
        self.path       = path
        self._functions = {}
        self._loaders   = []

    def initialize(self):
        loaders = self._loaders
        self._loaders = []     # Prevent recursion
        for loader in loaders:
            loader()

    def __getattr__(self, name):
        self.initialize()
        if name in self._functions:
            return self._functions[name]
        raise public.ExcFunction('"%s" has no function "%s"' % (self._name, name))

    def getFunctionName(self, name):
        return '%s.%s' % (self._name, name)

    def getFunction(self, name):
        self.initialize()
        if name in self._functions:
            return self._functions[name]
        return None

    def countFunctions(self):
        self.initialize()
        return len(self._functions)

    def addFunction(self, function):
        self.initialize()
        if function.nameShort in self._functions:
            return False
        self._functions[function.nameShort] = function
        return True

    def iterFunctionsSorted(self):
        self.initialize()
        namesFunction = self._functions.keys()
        namesFunction.sort()
        for nameFunction in namesFunction:
            yield self._functions[nameFunction]

    def addLoader(self, loader):
        self._loaders.append(loader)

    # Just to detect errant calls to module names, instead of functions
    def __call__(self, *args, **kwargs):
        raise public.ExcFunction('"%s" is a module, not a function' % self._name)

#===============================================================================

class ExportedModules:

    def __init__(self):
        self._exports = {}

    def add(self, name, path, loader):
        if name not in self._exports:
            self._exports[name] = ExportedModule(name, path)
        if loader:
            self._exports[name].addLoader(loader)
        return self._exports[name]

    def get(self, name):
        return self._exports.get(name, None)

    def has(self, name):
        return name in self._exports

    def getAll(self):
        return self._exports

    def loadAll(self):
        for name in self._exports:
            self._exports[name].initialize()

    def getModuleFunction(self, name):
        module = function = None
        f = name.split('.')
        # Non-core function?
        if len(f) == 2:
            if f[0] in self._exports:
                module   = self._exports[f[0]]
                function = module.getFunction(f[1])
        # Core function?
        elif len(f) == 1:
            if f[0] in symsCore:
                function = symsCore[f[0]]
        return (module, function)

    def iterSorted(self):
        namesExport = self._exports.keys()
        namesExport.sort()
        for nameExport in namesExport:
            yield self._exports[nameExport]

    def __iter__(self):
        for exportedModule in self._exports.values():
            yield exportedModule

#===============================================================================

class App(object):
    def __init__(self,
            pathRaw,
            createHome,
            dirsPathAdd,
            symsPublic = {},
            symsDoc    = {},
            book       = None,
            version    = versionEng):
        self.path = os.path.abspath(pathRaw)
        self.name = os.path.splitext(os.path.basename(pathRaw))[0]
        self.dir  = os.path.dirname(os.path.realpath(self.path))
        self.home = os.path.expanduser('~/.%s') % self.name
        if createHome and not os.path.isdir(self.home):
            log_utility.info('Creating directory "%s"...' % self.home)
            os.mkdir(self.home)
        self.shareGlobal  = os.path.join('/usr/share'      , self.name)
        self.shareLocal   = os.path.join('/usr/local/share', self.name)
        self.libGlobal    = os.path.join('/usr/lib'        , self.name)
        self.libLocal     = os.path.join('/usr/local/lib'  , self.name)
        self.etc          = os.path.join('/etc'            , self.name)
        self.subdirScript = '%s.d' % self.name
        self.dirs = [self.home]
        self.dirsPath = [self.home]
        # For install-free use look for script subdirs here or one up (for bin directory)
        if os.path.isdir(os.path.join(os.path.dirname(self.dir), self.subdirScript)):
            self.dirs.append(os.path.dirname(self.dir))
            self.dirsPath.append(os.path.dirname(self.dir))
        if os.path.isdir(os.path.join(self.dir, self.subdirScript)):
            self.dirs.append(self.dir)
            self.dirsPath.append(self.dir)
        self.dirs.extend([
            self.libLocal,
            self.libGlobal,
            self.shareLocal,
            self.shareGlobal,
            self.etc
        ])
        self.dirsPath.extend([
            self.libLocal,
            self.libGlobal,
            self.shareLocal,
            self.shareGlobal,
            self.etc
        ])
        self.dirsScript = [os.path.join(dir, self.subdirScript) for dir in self.dirs]
        self.namespace  = self.name.upper()
        self.exports    = ExportedModules()
        self.book       = book
        self.version    = version
        self.types      = {}
        self.symsPublic = symsPublic
        self.symsDoc    = symsDoc
        if dirsPathAdd:
            self.dirsPath.extend(dirsPathAdd)
    def loadAll(self):
        # For now always provide core documentation, even if we're not just
        # running the engine directly.
        #TODO: Should it be conditional?
        self.exports.loadAll()
        loadCoreDocumentation(self)

public.engine  = App(os.path.split(__file__)[0], True, [], public.__dict__, public._symsDoc)
public.program = App(sys.argv[0], True, public.engine.dirsPath)
if public.engine.name != public.program.name:
    public.engine.book = public.engine.name
sys.path = public.program.dirsPath + sys.path

#===============================================================================

class Function(object):

    '''A callable proxy for functions that validates and converts arguments
    based on @export decorator declarations.'''

    def __init__(self, name, nameShort, path, isInternal, func, defs, kwdefs):
        self.name       = name
        self.nameShort  = nameShort
        self.path       = path
        self.isInternal = isInternal
        self.func       = func
        self.defs       = defs
        self.kwdefs     = kwdefs
        self.doc        = func.__doc__
        self.lineno     = func.func_code.co_firstlineno
        self.more       = None
        self._fixDefs()     # Convert type classes to instances

    def __call__(self, *argsIn, **kwargsIn):

        iArg = kw = None

        if self.more is None and len(argsIn) > len(self.defs):
            if len(argsIn) > len(self.defs):
                if len(self.defs) == 0:
                    sQuantity = 'none'
                else:
                    sQuantity = 'only %d' % len(self.defs)
                raise public.ExcArgument('too many non-keyword arguments (%d), expected %s'
                                                % (len(argsIn), sQuantity))

        try:

            # Now we know that we have at least as many arguments as argument types
            argsOut   = []
            kwargsOut = {}

            # Validate and convert the arguments that have type definitions
            for iArg in range(len(self.defs)):
                # We need a default if an argument is missing
                if iArg < len(argsIn):
                    argIn = argsIn[iArg]
                else:
                    argIn = None
                argOut = self.defs[iArg].get(argIn)
                if argOut is None:
                    raise public.ExcArgument('missing argument')
                argsOut.append(argOut)

            # Take the remaining arguments after letting the More type convert it as needed.
            if self.more is not None:
                argsMore = argsIn[len(self.defs):]
                if len(argsMore) < self.more.countMin:
                    raise public.ExcArgument('minimum argument count is %d' % self.more.countMin)
                if len(argsMore) > self.more.countMax:
                    raise public.ExcArgument('maximum argument count is %d' % self.more.countMax)
                for argMore in argsMore:
                    argsOut.append(self.more.get(argMore))

            # Convert matching keyword arguments and take others as-is (if more is not None)
            # It's ok for keywords to be missing.
            for kw in kwargsIn:
                if kw in self.kwdefs:
                    argOut = self.kwdefs[kw].get(kwargsIn[kw])
                    if argOut is not None:
                        kwargsOut[kw] = argOut
                else:
                    raise public.ExcArgument('unrecognized keyword argument "%s"' % kw)

            # Fill in missing args that have defaults
            for kw in self.kwdefs:
                if kw not in kwargsOut:
                    default = self.kwdefs[kw].get(None)
                    if default is not None:
                        kwargsOut[kw] = default

            kw = iArg = None    # For exception handling below
            return self.func(*argsOut, **kwargsOut)

        except public.ExcBase, e:
            msgPairs = [('Function', '%s()' % self.name)]
            if kw is None:
                if iArg is not None:
                    msgPairs.append(('Argument', '#%d' % (iArg + 1)))
                    msgPairs.append(('Description', self.defs[iArg].desc))
            else:
                msgPairs.append(('Argument', kw))
                if kw in self.kwdefs:
                    msgPairs.append(('Description', self.kwdefs[kw].desc))
            msgPairs.append(('Error', e))
            msgs = ['%s: %s' % (mp[0], str(mp[1])) for mp in msgPairs]
            raise public.ExcFunction(*msgs)

    # Convert classes to instances in order to support a clean syntax for
    # parameter-less type specification.
    def _fixDefs(self):
        defsOut   = []
        kwdefsOut = {}
        more = None
        for i in range(len(self.defs)):
            argOut = fixDef(self.defs[i])
            if argOut is not None:
                # Special check that More is last
                if isinstance(argOut, public.More):
                    more = argOut
                    if i < len(self.defs) - 1:
                        raise public.ExcArgument('More should be last normal argument')
                else:
                    # Normal argument
                    defsOut.append(argOut)
            else:
                raise public.ExcArgument('"%s" argument %d not an TypeBase subclass.'
                                                % (self.name, i+1), str(self.defs[i]))
        for (kw, arg) in self.kwdefs.items():
            argOut = fixDef(arg)
            if argOut is not None:
                kwdefsOut[kw] = argOut
            else:
                raise public.ExcArgument('Bad @export keyword parameter "%s" for "%s"'
                            % (kw, self.name))
        self.defs   = defsOut
        self.kwdefs = kwdefsOut
        self.more   = more

    # Provide a prototype string with argument names
    def getProto(self):
        return '%s%s' % (self.name, strFuncArgs(self.func, False))

#===============================================================================

class DuplicateFunction(object):
    def __init__(self, function):
        self.function = function
    def __cmp__(self, other):
        i = cmp(self.name(), other.name())
        if i != 0:
            return i
        return cmp(self.path(), other.path())
    def name(self):
        return self.function.name
    def path(self):
        return self.function.func.func_code.co_filename,

#===============================================================================

def fixDef(arg):
    if isinstance(arg, public.TypeBase):
        return arg
    if inspect.isclass(arg) and issubclass(arg, public.TypeBase):
        try:
            return arg()
        except TypeError, e:
            raise public.ExcArgument('Bad definition for "%s"' % arg.__name__, str(e))
    return None

#===============================================================================

def getArgs():
    iFirst = 1
    smartArguments = True
    for arg in sys.argv[1:]:
        if arg[0] != '-':
            break
        iFirst += 1
        # Only look at options preceding all other arguments so that
        # negative numbers, etc. aren't rejected.
        if arg == '-e':
            smartArguments = False
        elif arg == '-v':
            public.verbose = doc.verbose = True
        elif arg == '-d':
            public.debug = doc.debug = structext.debug = True
        elif arg[0] == '-':
            log_utility.warning('Ignoring unknown option "%s"' % arg)
    if not smartArguments:
        return sys.argv[iFirst:]
    return public._getArgsCommands(sys.argv[iFirst:])

#===============================================================================

class FunctionNode(doc.Node):

    def __init__(self, function, nodes):
        if function.defs or function.more:
            optional = False
            rows = []
            namesArg = inspect.getargspec(function.func)[0]
            for i in range(len(function.defs)):
                if function.defs[i].hasDefault():
                    if function.defs[i].descDef:
                        sdef = ' (default = %s) [o]' % function.defs[i].descDef
                    else:
                        sdef = ' [o]'
                    optional = True
                else:
                    sdef = ''
                nodeArg  = doc.Node(form = 'cell', text = namesArg[i])
                nodeDesc = doc.Node(form = 'cell', text = '%s%s' % (function.defs[i].desc, sdef))
                rows.append(doc.Node(form = 'row', content = [nodeArg, nodeDesc]))
            if function.more:
                nodeArg  = doc.Node(form = 'cell', text = '<%s> ...' % function.more.desc)
                nodeDesc = doc.Node(form = 'cell', text = '(variable argument list)')
                rows.append(doc.Node(form = 'row', content = [nodeArg, nodeDesc]))
            nodeTable = doc.Node(
                    form    = 'table',
                    headers = ['Label', 'Description'],
                    content = rows)
            nodes.append(doc.Node(heading = 'Ordered Arguments', content = nodeTable))
            if optional:
                nodes.append('[o] = optional')
        if function.kwdefs:
            rows = []
            kws = function.kwdefs.keys()
            kws.sort()
            for kw in kws:
                if function.kwdefs[kw].descDef:
                    sdef = ' (default = %s)' % function.kwdefs[kw].descDef
                else:
                    sdef = ''
                nodeKw = doc.Node(form = 'cell', content = kw)
                nodeDesc = doc.Node(form = 'cell', content = function.kwdefs[kw].desc + sdef)
                rows.append(doc.Node(form = 'row', content = [nodeKw, nodeDesc]))
            nodeTable = doc.Node(
                    form    = 'table',
                    headers = ['Keyword', 'Description'],
                    content = rows)
            nodes.append(doc.Node(heading = 'Keyword Arguments (Optional)', content = nodeTable))
        names = function.name.split('.')
        if len(names) == 1:
            name = function.name
        else:
            name = '.'.join(names[1:])
        doc.Node.__init__(self, content = nodes)

#===============================================================================

def strFuncArgs(func, showDefaults):
    s = ''
    (args, varargs, varkw, defaults) = inspect.getargspec(func)
    for i in range(len(args)):
        if s:
            s += ', '
        s += args[i]
        if defaults:
            iDefault = i - len(args) + len(defaults)
            if iDefault >= 0:
                if showDefaults:
                    if text_utility.isString(defaults[iDefault]):
                        s += ' = "%s"' % defaults[iDefault]
                    else:
                        s += ' = %s' % defaults[iDefault]
                else:
                    s += '=?'
    if varargs is not None:
        if s:
            s += ', '
        s += '*%s' % varargs
    if varkw is not None:
        if s:
            s += ', '
        s += '**%s' % varkw
    return '(%s)' % s

def helpFunction(docRegistrar, namespace, func, doc):
    if namespace:
        name = '%s.%s' % (namespace, func.__name__)
    else:
        name = func.__name__
    if func.__doc__:
        if not doc:
            doc = func.__doc__
        else:
            doc += '\n'.join([doc, func.__doc__])
    if not doc:
        doc = '(undocumented function)'
    return docRegistrar.section('%s%s' % (name, strFuncArgs(func, True)), doc)

def helpClass(docRegistrar, namespace, cls, doc):
    if namespace:
        name = '%s.%s' % (namespace, cls.__name__)
    else:
        name = cls.__name__
    if cls.__doc__:
        if not doc:
            doc = cls.__doc__
        else:
            doc += '\n'.join([doc, cls.__doc__])
    if not doc:
        doc = '(undocumented class)'
    return docRegistrar.section(name, doc)

def helpVariable(docRegistrar, namespace, var, name, doc):
    if namespace:
        name = '%s.%s' % (namespace, name)
    if not doc:
        doc = '(undocumented %s)' % type(var).__name__
    return docRegistrar.section(name, doc)

def helpSymbols(docRegistrar, namespace, nameSection, symbols, filter, dictDoc = {}):
    nodeSection = None
    for sym in text_utility.sortedIter(symbols):
        if sym[0] != '_' and (not filter or filter(symbols[sym])):
            doc = dictDoc.get(sym)
            if nodeSection is None:
                nodeSection = docRegistrar.section('%s %s' % (namespace, nameSection))
            if inspect.isclass(symbols[sym]):
                nodeSection.add(helpClass(docRegistrar, namespace, symbols[sym], doc))
            elif inspect.isfunction(symbols[sym]):
                nodeSection.add(helpFunction(docRegistrar, namespace, symbols[sym], doc))
            else:
                nodeSection.add(helpVariable(docRegistrar, namespace, symbols[sym], sym, doc))
    return nodeSection

def loadCoreDocumentation(app):
    if app.name == public.engine.name and app != public.engine:
        return
    docRegistrar = doc.Registrar(app.name)
    props = {
        'all'      : app.namespace,
        'reference': '~%s' % app.namespace,  # '~' pushes to bottom of reference
    }
    if app.name == public.engine.name:
        props['core'] = app.namespace
    # Document nodes get stripped when set to None
    docRegistrar.section('%s Namespace' % app.namespace,
        helpSymbols(
            docRegistrar,
            app.namespace, 'Core Classes',
            app.symsPublic,
            inspect.isclass
        ),
        helpSymbols(
            docRegistrar,
            app.namespace,
            'Core Functions',
            app.symsPublic,
            inspect.isfunction
        ),
        helpSymbols(
            docRegistrar,
            app.namespace,
            'Core Variables',
            app.symsPublic,
            lambda o: (not inspect.isclass(o) and
                       not inspect.isfunction(o) and
                       not inspect.ismodule(o)),
            app.symsDoc
        ),
        helpSymbols(
            docRegistrar,
            app.namespace,
            'Exported Types',
            app.types,
            None
        ),
        **props
    )
    docRegistrar.register()

#===============================================================================
# NamespaceWrapper class
#
# Provides load-time API for function and documentation decorators, and
# documentation functions.  Collects un-closed decorators, fully-declared
# functions, and documentation nodes.
#===============================================================================

class NamespaceWrapper(object):

    class DecoratorExport:

        def __init__(self, isCore, isInternal, callback, *args, **kwargs):
            self.isCore     = isCore
            self.isInternal = isInternal
            self.callback   = callback
            self.function   = None
            self.args       = args
            self.kwargs     = kwargs
            self.handler    = self._register

        def __call__(self, *args, **kwargs):
            return self.handler(*args, **kwargs)

        def _register(self, func):
            # Check for a naked @CMDO.document decorator (bad)
            if not inspect.isfunction(func):
                raise public.ExcFunction('Bad @%s decorator', self.namespace)
            self.function = self.callback(func, self.isInternal, self.args, self.kwargs)
            # Return not seen when invoked without parens.  Handle calling here.
            self.handler = self._call
            return self.function

        def _call(self, *args, **kwargs):
            return self.function(*args, **kwargs)

    class DecoratorDoc:

        def __init__(self, callback, *args, **kwargs):
            self.callback = callback
            self.args     = args
            self.kwargs   = kwargs

        def __call__(self, func):
            if isinstance(func, Function):
                self.callback(func.func, func.nameShort, self.args, self.kwargs)
            else:
                self.callback(func, func.__name__, self.args, self.kwargs)
            return func

    def __init__(self, app, name, path, docRegistrar, isCore):
        # Public attributes
        self.doc = docRegistrar
        # Private attributes
        self._app        = app
        self._name       = name
        self._path       = path
        self._isCore     = isCore
        self._decoExport = []
        self._decoDoc    = []
        self._nodesFunc  = {}  # @document decorator contents by function name

    def __getattr__(self, name):
        if name in self._app.symsPublic:
            return self._app.symsPublic[name]
        if name in self._app.types:
            return self._app.types[name]
        if self._app.exports.has(name):
            return self._app.exports.get(name)
        raise public.ExcLoad('Unknown %s attribute "%s"' % (self._app.namespace, name))

    #=== Function decorators

    # The @export decorator for exported module-scope functions
    def export(self, *args, **kwargs):
        decorator = NamespaceWrapper.DecoratorExport(
                self._isCore, False, self._funcCallback, *args, **kwargs)
        self._decoExport.append(decorator)
        return decorator

    # The @internal decorator for exported functions that are invisible to help
    def internal(self, *args, **kwargs):
        decorator = NamespaceWrapper.DecoratorExport(
                self._isCore, True, self._funcCallback, *args, **kwargs)
        self._decoExport.append(decorator)
        return decorator

    # The @document decorator for function documentation
    def document(self, *args, **kwargs):
        decorator = NamespaceWrapper.DecoratorDoc(self._docCallback, *args, **kwargs)
        self._decoDoc.append(decorator)
        return decorator

    #=== Internal methods

    def _funcCallback(self, func, isInternal, args, kwargs):
        if self._name and not self._isCore:
            name = '%s.%s' % (self._name, func.__name__)
        else:
            name = func.__name__
        nameShort = func.__name__
        return Function(name, nameShort, self._path, isInternal, func, args, kwargs)

    def _docCallback(self, func, name, args, kwargs):
        self._nodesFunc.setdefault(name, []).append(doc.Node(content = args, **kwargs))

#===============================================================================

def loadScripts():

    if public.verbose:
        log_utility.info('Load %s modules from %s'
                        % (public.program.name, public.program.dirsScript))
        if public.program.name != public.engine.name:
            log_utility.info('Load %s modules from %s'
                            % (public.engine.name, public.engine.dirsScript))
        log_utility.info('Load Python modules from %s' % sys.path)

    # TODO: Load on demand, rather than sorting to get "_..." files containing
    # arg types and exceptions to come first.
    # For now type modules are just script modules that load early.

    # 1) Load engine core modules
    loaded = set()
    for dirCmdo in public.engine.dirsScript:
        paths = glob.glob(os.path.join(dirCmdo, '*%s') % public.extCore)
        paths.sort()
        for path in paths:
            name = os.path.splitext(os.path.split(path)[1])[0]
            if name in loaded:
                if public.verbose:
                    log_utility.info('Skipping duplicate engine core module "%s"' % path)
            else:
                loadScript(path, name, True, public.engine)
                loaded.add(name)

    # 2) Load named engine modules
    loaded = set()
    for dirCmdo in public.engine.dirsScript:
        paths = glob.glob(os.path.join(dirCmdo, '*%s') % public.extModule)
        paths.sort()
        for path in paths:
            name = os.path.splitext(os.path.split(path)[1])[0]
            if name in loaded:
                if public.verbose:
                    log_utility.info('Skipping duplicate engine module "%s"' % path)
            else:
                loader = ScriptLoader(path, name, public.engine)
                public.engine.exports.add(name, path, loader)
                loaded.add(name)

    # 3) Load engine documentation modules
    loaded = set()
    for dirCmdo in public.engine.dirsScript:
        paths = glob.glob(os.path.join(dirCmdo, '*%s') % public.extDoc)
        paths.sort()
        for path in paths:
            name = os.path.splitext(os.path.split(path)[1])[0]
            if name in loaded:
                if public.verbose:
                    log_utility.info('Skipping duplicate engine documentation module "%s"' % path)
            else:
                loader = DocumentationLoader(path, name, public.engine)
                public.engine.exports.add(name, path, loader)
                loaded.add(name)

    if public.program.name != public.engine.name:

        # 4) Load app core modules
        loaded = set()
        for dirCmdo in public.program.dirsScript:
            paths = glob.glob(os.path.join(dirCmdo, '*%s') % public.extCore)
            paths.sort()
            for path in paths:
                name = os.path.splitext(os.path.split(path)[1])[0]
                if name in loaded:
                    if public.verbose:
                        log_utility.info('Skipping duplicate core module "%s"' % path)
                else:
                    loadScript(path, name, True, public.engine, public.program)
                    loaded.add(name)

        # 5) Load named app modules
        loaded = set()
        for dirCmdo in public.program.dirsScript:
            paths = glob.glob(os.path.join(dirCmdo, '*%s') % public.extModule)
            paths.sort()
            for path in paths:
                name = os.path.splitext(os.path.split(path)[1])[0]
                if name in loaded:
                    if public.verbose:
                        log_utility.info('Skipping duplicate module "%s"' % path)
                else:
                    loader = ScriptLoader(path, name, public.engine, public.program)
                    public.program.exports.add(name, path, loader)
                    loaded.add(name)

        # 6) Load app documentation modules
        loaded = set()
        for dirCmdo in public.program.dirsScript:
            paths = glob.glob(os.path.join(dirCmdo, '*%s') % public.extDoc)
            paths.sort()
            for path in paths:
                name = os.path.splitext(os.path.split(path)[1])[0]
                if name in loaded:
                    if public.verbose:
                        log_utility.info('Skipping duplicate documentation module "%s"' % path)
                else:
                    loader = DocumentationLoader(path, name, public.engine, public.program)
                    public.engine.exports.add(name, path, loader)
                    loaded.add(name)

#===============================================================================

class ScriptLoader(object):

    def __init__(self, path, name, *apps):
        self.path = path
        self.name = name
        self.apps = apps

    def __call__(self):
        if public.verbose:
            log_utility.info('Loading "%s" on demand' % self.path)
        loadScript(self.path, self.name, False, *self.apps)

#===============================================================================

class DocumentationLoader(object):

    def __init__(self, path, name, *apps):
        self.path = path
        self.name = name
        self.apps = apps

    def __call__(self):
        if public.verbose:
            log_utility.info('Loading documentation in "%s" on demand' % self.path)
        loadDocumentation(self.path, self.name, *self.apps)

#===============================================================================

# Assumes the primary app is the last one
def loadScript(path, name, isCore, *apps):

    assert path

    try:

        if public.verbose:
            log_utility.info('Loading script "%s"...' % path)

        # Prepare the documentation registrar and namespace wrappers and exec the module
        # The last app passed in is considered the primary one
        appPrimary = apps[-1]

        docRegistrar = doc.Registrar(appPrimary.name)
        wrappers = []
        syms = {}
        for app in apps:
            wrappers.append(NamespaceWrapper(app, name, path, docRegistrar, isCore))
            syms[app.namespace] = wrappers[-1]
        doc.setStrucTextSymbols(syms)
        execfile(path, syms)

        # Warn about classes flagged for export (should be in a type module)
        # Export newly-discovered classes of appropriate ancestry
        namesOrig = [app.namespace for app in apps]
        for nameNew in syms:
            if nameNew not in namesOrig and inspect.isclass(syms[nameNew]):
                for exportedClass in exportedClasses:
                    sym = syms[nameNew]
                    if issubclass(sym, exportedClass):
                        if public.verbose:
                            log_utility.info('Register type "%s.%s"'
                                                % (appPrimary.namespace, nameNew))
                        appPrimary.types[nameNew] = sym

        # Create function objects for empty decorators (invoked without parens).
        # Register all discovered functions and track duplicates.
        if appPrimary.exports.has(name):
            export = appPrimary.exports.get(name)
        else:
            export = appPrimary.exports.add(name, path, None)
        global duplicateFunctions
        for wrapper in wrappers:
            for decorator in wrapper._decoExport:
                if decorator.function is None:
                    func = decorator.args[0]
                    decorator.args = decorator.args[1:]
                    decorator._register(func)
                if decorator.isCore:
                    if public.verbose:
                        log_utility.info('Register core function "%s"'
                                            % decorator.function.nameShort)
                    global symsCore
                    if decorator.function.nameShort not in symsCore:
                        symsCore[decorator.function.nameShort] = decorator.function
                else:
                    if public.verbose:
                        log_utility.info('Register function "%s.%s"'
                                            % (appPrimary.namespace, decorator.function.name))
                if not export.addFunction(decorator.function):
                    duplicateFunctions.append(DuplicateFunction(decorator.function))

        # Register documentation
        if export.countFunctions() > 0:
            # Documentation in function-bearing modules is added to the "reference"
            if appPrimary.namespace == public.program.namespace:
                props = {'all': name, 'reference': name}
            else:
                props = {}
            # For consistent TOC sorting need core to be None, rather than False.
            if isCore:
                nodeModule = docRegistrar.wrap(
                    form    = 'wrapper',
                    heading = 'Module: (%s)' % name,
                    core    = name,
                    **props
                )
            else:
                nodeModule = docRegistrar.wrap(
                    form    = 'wrapper',
                    heading = 'Module: %s' % name,
                    module  = name,
                    toc     = True,
                    **props
                )
            nodesBody = []
            for function in export.iterFunctionsSorted():
                if not function.isInternal:
                    nodesDoc = []
                    if function.doc:
                        nodesDoc.append(function.doc)
                    for wrapper in wrappers:
                        nodesDoc.append(wrapper._nodesFunc.get(function.nameShort, []))
                    nodesBody.append(
                        doc.Node(
                            form     = 'wrapper',
                            heading  = 'Function: %s' % function.getProto(),
                            content  = FunctionNode(function, nodesDoc),
                            function = function.name,
                            toc      = True,
                        )
                    )
            nodeModule.add(doc.Node(content = nodesBody))
        else:
            # Documentation in non-function-bearing modules is added to the "guide"
            if appPrimary.namespace == public.program.namespace:
                props = {'all': name, 'guide': name}
            else:
                props = {}
            if isCore:
                docRegistrar.wrap(form = 'wrapper', core = name, **props)
            else:
                docRegistrar.wrap(form = 'wrapper', module = name, **props)
        docRegistrar.register()

    except public.ExcLoad, e:
        log_utility._tracebackException('Failed to load "%s"' % path, e, 1, 1, False)
    except public.ExcBase, e:
        log_utility.error('Failed to load "%s"' % path, str(e))
    except doc.ExcBase, e:
        log_utility.error('Failed to load "%s" due to documentation error' % path, str(e))
    except Exception, e:
        log_utility._tracebackException('Failed to load "%s"' % path, e, 0, 0, True)

#===============================================================================

# Assumes the primary app is the last one
def loadDocumentation(path, name, *apps):

    assert path

    try:

        if public.verbose:
            log_utility.info('Loading documentation "%s"...' % path)

        # Prepare the documentation registrar and namespace wrappers and exec the module
        # The last app passed in is considered the primary one
        appPrimary = apps[-1]

        docRegistrar = doc.Registrar(appPrimary.name)
        wrappers = []
        syms = {}
        for app in apps:
            wrappers.append(NamespaceWrapper(app, name, path, docRegistrar, False))
            syms[app.namespace] = wrappers[-1]
        doc.setStrucTextSymbols(syms)

        # Documentation in non-function-bearing modules is added to the "guide"
        if appPrimary.namespace == public.program.namespace:
            props = {'all': name, 'guide': name}
        else:
            props = {}
        doc.parserStrucText.parse(open(path).read())
        node = doc.parserStrucText.take()
        node.setProp('module', name)
        docRegistrar.add(node)
        docRegistrar.register()

    except Exception, e:
        log_utility._tracebackException('Failed to load "%s"' % path, e, 0, 0, True)

#===============================================================================

def execute(sCmd):
    if public.verbose:
        log_utility.info('Execute: "%s"' % sCmd)
    # Restrict scope to public functions and runtime symbols.
    public.program.symsExec = copy.copy(symsCore)
    public.program.symsExec.update(public.engine.exports.getAll())
    public.program.symsExec[public.engine.namespace] = public
    if public.program.name != public.engine.name:
        public.program.symsExec.update(public.program.exports.getAll())
    if public.verbose:
        log_utility.info('=============== Symbols ===============')
        names = public.program.symsExec.keys()
        names.sort()
        for name in names:
            log_utility.info('%15s: %s' % (name, public.program.symsExec[name]))
        log_utility.info('=======================================')
    exec sCmd in public.program.symsExec

#===============================================================================

def main(version):
    if public.program.name != public.engine.name and version is not None:
        public.program.version = version
    args = getArgs()
    if public.verbose:
        log_utility.info('args = %s' % args)
    # Load scripts and warn about duplicates
    loadScripts()
    global duplicateFunctions
    if len(duplicateFunctions) > 0:
        duplicateFunctions.sort()
        for dup in duplicateFunctions:
            log_utility.warning('Ignoring duplicate "%s" from "%s"' % (dup.name(), dup.path()))
    # Display the quick start guide if running the base program with no arguments
    if public.engine.name and len(args) == 0:
        execute('help()')
        sys.exit(1)
    for argIn in args:
        try:
            execute(argIn)
        except public.ExcBase, e:
            if e.traceback:
                log_utility._tracebackException(None, e, 0, 0, False)
            else:
                msgs = str(e).split('\n')
                log_utility.error('Command: "%s"' % argIn, *msgs)
        except doc.ExcBase, e:
            msgs = str(e).split('\n')
            log_utility.error('Command: "%s"' % argIn, *msgs)
        except public.ExcQuit, e:
            log_utility.info('<quit>')
            sys.exit(1)
        except Exception, e:
            skipTop = 4
            if public.verbose:
                skipTop = 0
            log_utility._tracebackException('Command: %s' % argIn, e, skipTop, 0, True)
