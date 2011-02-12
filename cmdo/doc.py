#===============================================================================
#===============================================================================
# Doc - documentation generator for Cmdo
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
import os
import copy
import tempfile
import text_utility
import sys_utility
import structext

debug = False
verbose = False

# List of top level nodes used to seed queries
nodesTop = []

# Set of all unique property names
namesProp = set()

# The property names that are hidden from the user in the catalog
namesPropInternal = [
    'book',
    'form',
    'headers',
    'heading',
    'style',
    'text',
    'toc',
    'tocheading',
    'tocid',
]

# Node forms that automatically wrap unwrapped sub-nodes
formAutoWrappers = {
    'list'    : 'item',
    'table'   : 'row',
    'row'     : 'cell',
}

# Exceptions
class ExcBase(Exception): pass

#===============================================================================

class Registrar(object):

    def __init__(self, book):
        self._book = book
        self._nodesPending = []

    #=== Public document-building methods

    def block(self, *content, **props):
        return self._wrapNodes(['block'], *content, **props)

    def table(self, headers = [], *content):
        return self._wrapNodes(['table', 'row', 'cell'], headers = headers, *content)

    # "style" can be "number", "bullet" or nothing (no decoration used).
    def list(self, style, *content):
        if style is not None:
            style = style.lower()
        if style and (not text_utility.isString(style) or style not in ('bullet', 'number')):
            raise ExcBase('Bad list style "%s"' % style)
        return self._wrapNodes(['list', 'item'], style = style, *content)

    def link(self, url, text = None):
        self._nodesPending.append(Node(form = 'link', url = url, text = text))
        return self._nodesPending[-1]

    def plain(self, *content):
        return self._wrapNodes(['plaintext'], *content)

    def section(self, heading, *content, **props):
        return self._wrapNodes([], toc = True, heading = heading, *content, **props)

    #=== Other public methods

    # Wrap previously-added nodes in a wrapper node
    def wrap(self, **props):
        self._nodesPending = [Node(content = [node for node in self._iterTopNodes()], **props)]
        return self._nodesPending[0]

    # Add node created externally to pending list for later registration in register()
    def add(self, *nodes):
        self._nodesPending.extend(nodes)

    def register(self):
        global nodesTop
        for node in self._nodesPending:
            if not node.parent() and self._book:
                node.setProp('book', self._book)
                nodesTop.append(node)
        self._nodesPending = []

    #=== Public methods

    def query(self, *args, **kwargs):
        return query(*args, **kwargs)

    def select(self, *args, **kwargs):
        return selectNodes(*args, **kwargs)

    # Generate list of unique non-internal keywords.
    def getKeywords(self):
        names = list(namesProp)
        names.sort()
        return [name for name in names if name not in namesPropInternal]

    # Catch attempts to call directly to provide a better error
    def __call__(self, *args, **kwargs):
        raise ExcBase('Cannot call document registrar object')

    #=== Internal methods

    def _iterTopNodes(self):
        for node in self._nodesPending:
            if not node.parent():
                yield node

    def _wrapNodes(self, forms, *content, **props):
        # See if we can just reuse a single content node.
        node = None
        if content and len(content) == 1 and isinstance(content[0], Node):
            # We can reuse if we're not given a form or the content node isn't
            # assigned one or the content node is already the correct form.
            form = content[0].getProp('form')
            if not forms or not form or forms[0] == form:
                node = content[0]
                if props:
                    node.setProps(props)
        # Wrap the content if it isn't itself a reusable node.
        if not node:
            content2 = self._prepareNodes(forms[1:], content, True)
            if len(forms) > 0:
                node = Node(content = content2, form = forms[0], **props)
            else:
                node = Node(content = content2, **props)
            self._nodesPending.append(node)
        return node

    def _prepareNodes(self, forms, items, major, **props):
        ddd = forms == ['item']
        if type(items) is not list and type(items) is not tuple:
            items = [items]
        nodes = []
        for item in items:
            if isinstance(item, Node):
                node = item
                if len(forms) > 0 and node.getProp('form') != forms[0]:
                    node = Node(content = node, form = forms[0], **props)
                nodes.append(node)
                if props:
                    item.setProps(props)
                if major:
                    self._nodesPending.append(nodes[-1])
            else:
                props2 = copy.copy(props)
                if len(forms) > 1:
                    props2['content'] = self._prepareNodes(forms[1:], item, False)
                elif text_utility.isString(item) and 'text' not in props2:
                    props2['text'] = item
                else:
                    props2['content'] = item
                if len(forms) > 0:
                    props2['form'] = forms[0]
                nodes.append(Node(**props2))
                if major:
                    self._nodesPending.append(nodes[-1])
        return nodes

#===============================================================================

# Arguments:
#   nodesIn: initial set of nodes to query
#     where: function to accept (==True) a node's properties
#   orderBy: property names determining sort order
#
# Defaults:
#   nodesIn: the global list of top-level nodes (nodesTop)
#     where: accepts all top-level nodes
#   orderBy: no sorting
def query(nodesIn = nodesTop, where = None, orderBy = []):
    if nodesIn is None:
        nodesIn = nodesTop
    nodesOut = selectNodes(nodesIn, where = where)
    if nodesOut and orderBy:
        nodesOut.sort(NodeOrderer(orderBy))
    return nodesOut

# Search for highest level nodes matching a "where" clause (function).  Can
# return nodes from more than one level, but won't return a matching child,
# once a parent is matched.
def selectNodes(nodes, where = None, level = 0, countMax = 0):
    nodesSel = []
    for node in nodes:
        if not where or where(node._props):
            nodesSel.append(node)
        else:
            nodesChk = [node for node in node.iterNodes()]
            level2 = level + 1
            countMax2 = countMax - len(nodesSel)
            nodesAdd = selectNodes(nodesChk, where = where, level = level2, countMax = countMax2)
            if nodesAdd:
                nodesSel.extend(nodesAdd)
        if countMax > 0 and len(nodesSel) >= countMax:
            break
    return nodesSel

class NodeOrderer(object):
    def __init__(self, orderBy):
        self.orderBy = orderBy
    def __call__(self, node1, node2):
        if self.orderBy:
            for key in self.orderBy:
                v1 = node1.getProp(key, inherit = True)
                v2 = node2.getProp(key, inherit = True)
                if v1 < v2:
                    return -1
                if v1 > v2:
                    return +1
        return 0

countTOC = 0

# Generate Table of Contents
def getTOC(tocStart = 0, tocStop = 1, nodesIn = nodesTop, book = None, orderBy = [], **props):
    if tocStart < 0 or tocStop <= tocStart:
        return None
    # Filter by book?  Always take core stuff.
    if book:
        nodesIn = query(nodesIn = nodesIn, where = lambda o: o.book == book or o.core)
    # Get the top level nodes
    nodes   = query(nodesIn = nodesIn, where = lambda o: o.toc, orderBy = orderBy)
    content = _generateTOCNodes(tocStart, tocStop, 0, nodes)
    if not content:
        return None
    return Node(form = 'toc0', content = content, **props)

def _generateTOCNodes(tocStart, tocStop, level, nodesIn):
    level += 1
    nodesOut = []
    if level > tocStart:
        tocForm = 'toc%d' % (level - tocStart)
    else:
        tocForm = None
    for nodeIn in nodesIn:
        if nodeIn.isEmpty():
            continue
        global countTOC
        countTOC += 1
        # Give the source node a TOC id so that links have a target
        tocid = 'tocitem%d' % countTOC
        nodeIn.setProp('tocid', tocid)
        # Descend to children?
        content = None
        if level < tocStop:
            nodesInSub = query(nodesIn = nodeIn.getChildren(), where = lambda o: o.toc)
            if nodesInSub:
                content = _generateTOCNodes(tocStart, tocStop, level, nodesInSub)
        if tocForm is not None:
            nodesOut.append(
                Node(
                    form       = tocForm,
                    content    = content,
                    toclink    = tocid,
                    tocheading = nodeIn.getProp('heading'),
                )
            )
        else:
            nodesOut.extend(content)
    return nodesOut

#===============================================================================

class PublishContext(object):
    '''Stack used to track publishing state'''

    class ContextData(object):
        def __init__(self, props, breadth):
            self.props = props
            self.breadth = breadth
            self.cache   = {}

    def __init__(self, tocFunc, tocStart, tocStop, *streams):
        self.tocFunc  = tocFunc     # This is a call-back function
        self.tocStart = tocStart
        self.tocStop  = tocStop
        self.streams  = streams
        self.levels   = [PublishContext.ContextData({}, 0)]

    def feedTOC(self, publisher):
        if self.tocFunc and self.tocStop - self.tocStart > 0:
            self.tocFunc(self, publisher, self.tocStart, self.tocStop)

    def push(self, props, breadth):
        data = PublishContext.ContextData(props, breadth)
        self.levels.append(data)

    def pop(self):
        return self.levels.pop()

    def write(self, s):
        for stream in self.streams:
            stream.write(s)

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def getBreadth(self, level = 0):
        assert level >= 0 and level < len(self.levels)
        return self.levels[-1 - level].breadth

    def getDepth(self):
        return len(self.levels)

    def iterLevelsBottomUp(self, level = 0):
        assert level >= 0 and level < len(self.levels)
        for i in range(len(self.levels) - 1 - level, -1, -1):
            yield self.levels[i]

    def iterLevelsTopDown(self, level = 0):
        assert level >= 0 and level < len(self.levels)
        for i in range(len(self.levels) - level):
            yield self.levels[i]

    def getCache(self, name, default = None, level = 0, inherit = False):
        assert level >= 0 and level < len(self.levels)
        if inherit:
            for data in self.iterLevelsBottomUp(level = level):
                if name in data.cache:
                    return data.cache[name]
        else:
            if name in self.levels[-1 - level].cache:
                return self.levels[-1 - level].cache[name]
        return default

    def hasCache(self, name, level = 0, inherit = False):
        return self.getCache(name, level = level, inherit = inherit) is not None

    # Get and remove
    def takeCache(self, name, default = None, level = 0, inherit = False):
        assert level >= 0 and level < len(self.levels)
        found = None
        if inherit:
            for data in self.iterLevelsBottomUp(level = level):
                if name in data.cache:
                    found = data
                    break
        else:
            if name in self.levels[-1 - level].cache:
                found = self.levels[-1 - level]
        if found is not None:
            val = found.cache[name]
            del found.cache[name]
        else:
            val = None
        return val

    # Get and increment - return value before incrementing
    def getCacheIncrement(self, name, level = 0, inherit = False):
        assert level >= 0 and level < len(self.levels)
        found = None
        if inherit:
            for data in self.iterLevelsBottomUp(level = level):
                if name in data.cache:
                    found = data
                    break
        else:
            if name in self.levels[-1 - level].cache:
                found = self.levels[-1 - level]
        if found is not None:
            val = found.cache[name]
            found.cache[name] = val + 1
        else:
            val = 0
            self.levels[-1 - level].cache[name] = 1
        return val

    def setCache(self, name, value, level = 0, inherit = False):
        assert level >= 0 and level < len(self.levels)
        if inherit:
            for data in self.iterLevelsBottomUp(level = level):
                if name in data.cache:
                    data.cache[name] = value
                    return
        self.levels[-1 - level].cache[name] = value

    def copyCache(self, nameFrom, nameTo, level = 0, inherit = False):
        value = self.getCache(nameFrom, level = level, inherit = inherit)
        self.setCache(nameTo, value, level = level, inherit = inherit)
        return value

    def moveCache(self, nameFrom, nameTo, level = 0, inherit = False):
        value = self.getCache(nameFrom, level = level, inherit = inherit)
        self.setCache(nameTo, value, level = level, inherit = inherit)
        self.setCache(nameFrom, None, level = level, inherit = inherit)
        return value

    # Get all instances of a cache item up the level stack
    def getCacheStack(self, name, level = 0):
        vals = []
        for data in self.iterLevelsBottomUp(level = level):
            if name in data.cache:
                vals.append(data.cache[name])
        return vals

    def appendCacheString(self, name, s, level = 0, inherit = False):
        value = self.getCache(name, default = '', level = level, inherit = inherit)
        self.setCache(name, value + s, level = level, inherit = inherit)

    def cacheProp(self, name, nameTo = None, level = 0, inherit = False):
        if nameTo is None:
            nameTo = name
        if self.hasProp(name, level = level, inherit = inherit):
            value = self.getProp(name, level = level, inherit = inherit)
            self.setCache(nameTo, value, level = level, inherit = inherit)

    def getProp(self, name, default = None, level = 0, inherit = False):
        assert level >= 0 and level < len(self.levels)
        if inherit:
            for data in self.iterLevelsBottomUp(level = level):
                if name in data.props:
                    return data.props[name]
        else:
            if name in self.levels[-1 - level].props:
                return self.levels[-1 - level].props[name]
        return default

    # Get all instances of a property up the level stack
    def getPropsStack(self, name, level = 0):
        vals = []
        for data in self.iterLevelsBottomUp(level = level):
            if name in data.props:
                vals.append(data.props[name])
        return vals

    def hasProp(self, name, level = 0, inherit = False):
        return (self.getProp(name, level = level, inherit = inherit) is not None)

    def getAllProps(self, level = 0, inherit = False):
        assert level >= 0 and level < len(self.levels)
        if inherit:
            props = {}
            for data in self.iterLevelsBottomUp(level = level):
                for key in data.props:
                    if key not in props:
                        props[key] = data.props[key]
            return props
        return self.levels[-1 - level].props

    # Move text up one level and append (with separator) to cache property
    # Returns False on failure.
    def consolidateCacheText(self, name, sep):
        if len(self.levels) < 2:
            return False
        if name not in self.levels[-1].cache:
            return False
        text = self.levels[-1].cache[name]
        if not text or not text_utility.isString(text):
            return False
        if name in self.levels[-2].cache:
            textUp = self.levels[-2].cache[name]
        else:
            textUp = None
        if textUp:
            self.levels[-2].cache[name] = '%s%s%s' % (textUp.rstrip(), sep, text.lstrip())
        else:
            self.levels[-2].cache[name] = text
        del self.levels[-1].cache[name]
        return True

    def dump(self, f = None):
        if f is None:
            f = sys.stdout
        indent = ''
        f.write('----------------------\n')
        for level in self.levels:
            f.write('%s%s\n' % (indent, str(level.cache)))
            indent += '  '
        f.write('----------------------\n')

#===============================================================================
# Node - a physical node in the documentation tree
#===============================================================================

class Node(object):
    '''A concrete documentation node.  Accepts content as lists, tuples,
    strings and nodes.  Automatically wraps content in container nodes, e.g.
    table, in nodes of the appropriate type, e.g. row.'''

    # Dictionary that allows access through pseudo-attributes for cleaner
    # syntax in "where" clauses.
    class Props(dict):
        def __getattr__(self, name):
            return self.get(name)

    def __init__(self, content = [], nodeParent = None, **props):
        self._nodesChild = []
        self._nodeParent = nodeParent
        self._props = Node.Props()
        for name in props:
            self.setProp(name, props[name])
        if content:
            form = self.getProp('form')
            # Check for special processing of containers like lists, tables, rows, cells, etc.
            if form in formAutoWrappers and (type(content) is list or type(content) is tuple):
                formItem = formAutoWrappers[form]
                # If anything is an explicit item node just take the nodes as is
                for item in content:
                    if (item is not None
                            and issubclass(item.__class__, Node)
                            and item.getProp('form') == formItem):
                        break
                # If nothing is an explicit item node wrap all the nodes/strings as items.
                else:
                    content = [Node(content = item, form = formItem)
                                    for item in content if item is not None]
            self.add(content)

    def add(self, content):
        nStart = len(self._nodesChild)
        if isinstance(content, Node) or text_utility.isString(content):
            items = [content]
        else:
            # Allow, but strip out null items
            items = [item for item in content if item is not None]
        for item in items:
            if item:
                if isinstance(item, Node):
                    node = item
                # Naked lists/tuples become nodes
                elif type(item) is list or type(item) is tuple:
                    node = Node(content = item)
                # Naked strings become nodes with the text property set
                elif text_utility.isString(item):
                    # Parse structured text to produce nodes.
                    parserStrucText.parse(item)
                    node = parserStrucText.take()
                if node is not None:
                    node._nodeParent = self
                    self._nodesChild.append(node)
        # Simplify the structure by looking for special cases.
        self._optimize()

    def parent(self):
        return self._nodeParent

    def getProp(self, name, default = None, inherit = False):
        if inherit:
            if not self.hasProp(name) and self._nodeParent:
                return self._nodeParent.getProp(name, default = default, inherit = inherit)
        return self._props.get(name, default)

    def hasProp(self, name, inherit = False):
        return (self.getProp(name, inherit = inherit) is not None)

    def setProp(self, name, value):
        global namesProp
        if name not in namesProp:
            namesProp.add(name)
        self._props[name] = value

    def setProps(self, props):
        if props:
            for key in props:
                val = props[key]
                # Delete props being forced to None
                if val is None:
                    if key in self._props:
                        del self._props[key]
                else:
                    self.setProp(key, val)

    def getProps(self):
        return self._props

    def iterNodes(self):
        for node in self._nodesChild:
            yield node

    def getChildren(self):
        return self._nodesChild

    def nodeCount(self):
        return len(self.getChildren())

    def isEmpty(self):
        return (len(self._nodesChild) == 0 and not self.hasProp('text'))

    def iterAncestryUp(self, includeSelf = True, selector = None):
        if includeSelf:
            if not selector or selector(self):
                yield self
        node = self.parent()
        while node is not None:
            if not selector or selector(node):
                yield node
            node = node.parent()

    def iterAncestryDown(self, includeSelf = True, selector = None):
        lineage = [node for node in self.iterAncestryUp(includeSelf = includeSelf)]
        while len(lineage) > 0:
            node = lineage.pop()
            if not selector or selector(node):
                yield node

    def publish(self, publisher,
            output   = None,
            view     = False,
            tocStart = 0,
            tocStop  = 2,
            style    = None):

        if self.hasProp('title'):
            title = self.getProp('title')
        elif self.hasProp('heading'):
            title = self.getProp('heading')
        else:
            title = 'document'

        # If we're viewing the file we may need to create a temp file
        if view:
            if output:
                viewer = self._getPublisherFileViewer(publisher, output)
            else:
                name = title.replace(':', '_').replace(' ', '_')
                nameFile = 'doc_%s%s' % (name, publisher.extension)
                tmp = os.path.join(tempfile.gettempdir(), nameFile)
                viewer = self._getPublisherFileViewer(publisher, tmp)
                if viewer:
                    output = tmp
        else:
            viewer = None

        # Open specified file or use stdout
        if output:
            print 'Publishing to "%s"' % output
            f = open(output, 'w')
        else:
            f = sys.stdout

        # This is the stack used by the publisher to manage and access state
        context = PublishContext(self.publishTOC, tocStart, tocStop, f)

        publisher.docBegin(context, title, style)

        self._publish(publisher, context, 0)

        publisher.docEnd(context)

        # Close the file (not stdout) and view, if necessary
        if f != sys.stdout:
            f.close()
        if viewer is not None:
            viewer.run()

    # Called-back from publisher through the context when the publisher wants
    # to inject the table of contents.
    def publishTOC(self, context, publisher, tocStart, tocStop):
        node = getTOC(tocStart = tocStart, tocStop = tocStop, nodesIn = self.getChildren())
        if node:
            node._publish(publisher, context, 0)

    def _publish(self, publisher, context, nNode):

        # Set up the publishing context
        context.push(self.getProps(), self.nodeCount())
        context.setCache('nNode', nNode)

        publisher.nodeBegin(context)

        # Publish child nodes
        nNodeChild = 0
        for node in self.iterNodes():
            node._publish(publisher, context, nNodeChild)
            nNodeChild += 1

        publisher.nodeEnd(context)

        context.pop()

    def _dump(self, f = None, level = 0):
        if f is None:
            f = sys.stdout
        f.write('%s:%s: %s\n' % ('    ' * level, self.__class__.__name__, self.getProps()))
        for node in self.iterNodes():
            if text_utility.isString(node):
                f.write('%s\'\'\'%s\'\'\'\n' % ('    ' * (level+1), node))
            else:
                node._dump(f, level+1)

    def _getPublisherFileViewer(self, publisher, path):
        if text_utility.isString(publisher.types):
            viewer = sys_utility.getViewer(path, publisher.types)
        else:
            viewer = sys_utility.getViewer(path, *publisher.types)
        if not viewer:
            print 'No viewer found for types: %s' % str(publisher.types)
        return viewer

    # Simplify the structure by looking for the special case of a single child
    # node where the parent has nothing but a form property and the child is a
    # "block" form or has no form.  Also, don't simplify when the node is a
    # subclass.
    def _optimize(self):
        form = self.getProp('form')
        if form:
            # We don't want overlapping properties to merge.  The property
            # 'form' gets special handling.
            keysProp = set([key for key in self._props if key != 'form'])
            while (len(self._nodesChild) == 1 and
                   self._nodesChild[0].getProp('form', default = 'block') == 'block' and
                   self._nodesChild[0].__class__ == self.__class__ and
                   not keysProp.intersection(set(self._nodesChild[0]._props))):
                self._props.update(self._nodesChild[0]._props)
                self._nodesChild = self._nodesChild[0]._nodesChild
                self.setProp('form', form)
                # The original child node is now orphaned

#===============================================================================

# The Node class serves well as the factory since the constructor understands
# the attributes provided by the parser and returns an object.
parserStrucText = structext.Parser(Node, {})

def setStrucTextSymbols(syms):
    global parserStrucText
    parserStrucText = structext.Parser(Node, syms)
