#!/usr/bin/env python
#===============================================================================
#===============================================================================
# Structext - structured text parser used for, but independent of, Cmdo
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

#===============================================================================
# Client Requirements:
#
#   The only requirements of a module client are to implement a callable
#   factory, implement a node class with an add method, and provide a
#   dictionary for macro evaluation.  Here are the specifics...
#
#   - The Parser constructor receives a factory object and a symbol dictionary.
#
#   - The symbol dictionary is used for evaluating {{...}} macros.
#
#   - The factory must be callable, i.e. by implementing the __call__ method or
#     by being a function or method.
#
#   - The factory must accept and use the following keyword arguments:
#       form    = (None, "list", "item", "table", "row", "cell", "link",
#                  "block", or "plaintext")
#       text    = <string>
#       heading = <section heading text>
#       toc     = True on section nodes
#       style   = (None, "bullet", or "number")
#       headers = <table header (string) list>
#       url     = <link URL>
#
#       The "style" keyword is only used as a form=list modifier.
#
#   - The factory must return an object representing a documentation node.
#     - The returned node object must support an "add" method.
#     - The add method is called to inform the node about a new child node.
#     - The add method's only argument is a child node object.
#
# Syntax:
#   See DEVELOPMENT or development.html for full syntax.
#===============================================================================

import re

# Eval block regular expression
reEval = re.compile('(?<!\{)'       # no preceding '{'
                    '(\{\{)'        # *Group 1* "{{"
                    '(?!\{)'        # no extra '{'
                    '[ \t]*'        # ignore ws before content
                    '(.*?)'         # *Group 2* content
                    '[ \t]*'        # ignore ws after content
                    '(\}\})'        # *Group 3* "}}"
                    '(?!\})')       # no trailing '}'
# Link block regular expression
reLink = re.compile('(?<!\[)'       # no preceding '['
                    '(\[\[)'        # *Group 1* "[["
                    '(?!\[)'        # no extra '['
                    '(?:'           # optional <label>=
                        '[ \t]*'    # ignore ws before <label>=
                        '([^=]*?)'  # *Group 2* <label>
                        '[ \t]*='   # ignore ws after <label> / before '='
                    ')?'
                    '[ \t]*'        # ignore ws before URL
                    '([^\]]*?)'     # *Group 3* URL
                    '[ \t]*'        # ignore ws after URL
                    '(\]\])'        # *Group 4* "]]"
                    '(?!\])')       # no trailing ']'

debug = False

def _isBlockStart(line):
    s = line.lstrip()
    return (s[:1] in '!#*|' or s[:3] in ('"""', "'''", '{{{'))

#===============================================================================

class TextBlock(object):

    @staticmethod
    def start(line):
        if _isBlockStart(line):
            return None
        return TextBlock(line.strip())

    def __init__(self, sText):
        self.sText = sText

    def parse(self, line):
        if _isBlockStart(line):
            return line
        s = line.strip()
        if self.sText:
            self.sText += ' '
        self.sText += s
        return None

    def flush(self, doc, symsGlobal, symsLocal):
        sText = self.sText.strip()
        if sText:
            nodeRoot = parseString(sText, doc, symsGlobal, symsLocal, False, form = 'block')
            doc.sections[-1].add(nodeRoot)
        self.sText = ''

    def __str__(self):
        return 'Text("%s")' % self.sText

#===============================================================================

class PlaintextBlock(object):

    @staticmethod
    def start(line):
        s = line.strip()
        if s[:3] == '"""' or s[:3] == "'''":
            return PlaintextBlock(s[3:], s[:3])
        return None

    def __init__(self, sText, sTerm):
        self.sText = sText
        self.sTerm = sTerm

    def parse(self, line):
        i = line.find(self.sTerm)
        if i >= 0:
            s = line[:i]
        else:
            s = line
        if self.sText:
            self.sText += '\n'
        self.sText += s
        if i >= 0:
            return s[i+3:]
        return None

    def flush(self, doc, symsGlobal, symsLocal):
        sText = self.sText.rstrip()
        if sText:
            nodeRoot = parseString(sText, doc, symsGlobal, symsLocal, False, form = 'plaintext')
            doc.sections[-1].add(nodeRoot)
        self.sText = ''

    def __str__(self):
        return 'Plaintext("%s")' % self.sText

#===============================================================================

class ExecBlock(object):

    @staticmethod
    def start(line):
        s = line.strip()
        if s[:3] == '{{{':
            block = ExecBlock()
            block.parse(s[3:])
            return block
        return None

    def __init__(self):
        self.sText = ''

    def parse(self, line):
        i = line.find('}}}')
        if i >= 0:
            s = line[:i]
        else:
            s = line
        if s:
            if self.sText:
                self.sText += '\n'
            self.sText += s
        if i >= 0:
            return s[i+3:]
        return None

    def flush(self, doc, symsGlobal, symsLocal):
        sText = self.sText.strip()
        if sText:
            try:
                exec sText in symsGlobal, symsLocal
            except Exception, e:
                print '%s\n{{{\n%s\n}}}' % (str(e), sText)
        self.sText = ''

    def __str__(self):
        return 'Exec("%s")' % self.sText

#===============================================================================

class HeadingBlock(object):

    @staticmethod
    def start(line):
        s = line.strip()
        level = 0
        while len(s) > level and s[level] == '!':
            level += 1
        if level > 0:
            return HeadingBlock(level, s[level:].lstrip())
        return None

    def __init__(self, level, sText):
        self.level = level
        self.sText = sText

    def parse(self, line):
        # Continuation?
        s = line.strip()
        if s and s[0] == '+':
            s = s[1:]
            if s:
                if self.sText:
                    self.sText += ' '
                self.sText += s
            return None
        # Don't want this line (not a continuation)
        return line

    def flush(self, doc, symsGlobal, symsLocal):
        sText = self.sText.strip()
        # Truncate the stack to handle incoming level
        if self.level < len(doc.sections):
            doc.sections = doc.sections[:self.level]
        # Expand macros and links and create section node with heading and TOC flag
        sOut = expandString(sText, symsGlobal, symsLocal)
        if sOut:
            doc.sections.append(doc.factory(heading = sOut, toc = True))
            doc.sections[-2].add(doc.sections[-1])
        # Lists start fresh in each section
        self.sText = ''

    def __str__(self):
        return 'Heading(%d, "%s")' % (self.level, self.sText)

#===============================================================================

class ListBlock(object):

    @staticmethod
    def start(line):
        s = line.lstrip()
        if s[:1] not in '*#':
            return None
        block = ListBlock()
        block.parse(line)
        return block

    class Item(object):
        def __init__(self, sText):
            self.sText = sText

    class List(object):
        def __init__(self, level, style):
            self.level = level
            self.style = style
            self.items = []
        def add(self, level, style, sText):
            assert level >= self.level
            if level == self.level:
                self.items.append(ListBlock.Item(sText))
                return self.items[-1]
            if len(self.items) == 0 or not isinstance(self.items[-1], ListBlock.List):
                self.items.append(ListBlock.List(self.level+1, style))
            return self.items[-1].add(level, style, sText)
        def emit(self, doc, nodeContainer, symsGlobal, symsLocal, wrapList):
            # Items are either sub-list or text items.
            for item in self.items:
                # Sub-list item?
                if isinstance(item, ListBlock.List):
                    nodeListSub = doc.factory(form = 'list', style = item.style)
                    if wrapList:
                        nodeItem = doc.factory(form = 'item')
                        nodeItem.add(nodeListSub)
                        nodeContainer.add(nodeItem)
                    else:
                        nodeContainer.add(nodeListSub)
                    item.emit(doc, nodeListSub, symsGlobal, symsLocal, True)
                # Text item?
                else:
                    nodeItem = parseString(
                            item.sText, doc, symsGlobal, symsLocal, False, form = 'item')
                    nodeContainer.add(nodeItem)

    def __init__(self):
        self.root = ListBlock.List(0, None)
        self.last = None

    # Parsing builds the Item object tree
    def parse(self, line):
        s = line.strip()
        # Continue the current list item? (leading '+')
        if self.last is not None and s and s[0] == '+':
            s = s[1:]
            if s:
                self.last.sText += ' '
                self.last.sText += s
            return None
        # Grab list prefix.
        level = 0
        while level < len(s) and s[level] in '*#':
            level += 1
        # Not a list item?
        if level == 0:
            return line
        # Add a list item.
        if s[0] == '*':
            style = 'bullet'
        elif s[0] == '#':
            style = 'number'
        else:
            style = None
        sText = s[level:].lstrip()
        self.last = self.root.add(level, style, sText)
        return None

    # Flushing reads the Item object tree to generate nodes
    def flush(self, doc, symsGlobal, symsLocal):
        self.root.emit(doc, doc.sections[-1], symsGlobal, symsLocal, False)
        self.root = ListBlock.List(0, None)

    def __str__(self):
        return 'List(%s)' % ['%s(%d)' % (list.style, len(list.items)) for list in self.root.items]

#===============================================================================

class TableBlock(object):

    @staticmethod
    def start(line):
        s = line.lstrip()
        if s[:1] != '|':
            return None
        block = TableBlock()
        block.parse(line)
        return block

    def __init__(self):
        self.rows = []
        self.lastRowClosed = False

    def parse(self, line):
        s = line.strip()
        if not s:
            return None
        rowClosed = (s[-1] == '|')
        # Continue the current row? (leading '+')
        if len(self.rows) > 0 and s and s[0] == '+':
            s = s[1:]
            if s:
                if rowClosed:
                    ssCell = [cell.strip() for cell in s.split('|')[:-1]]
                else:
                    ssCell = [cell.strip() for cell in s.split('|')]
                if ssCell:
                    if self.lastRowClosed or len(self.rows[-1]) == 0:
                        self.rows[-1].extend(ssCell)
                    else:
                        if self.rows[-1][-1]:
                            self.rows[-1][-1] += ' '
                        self.rows[-1][-1] += ssCell[0]
                        self.rows[-1].extend(ssCell[1:])
                        self.lastRowClosed = (s[-1] == '|')
            return None
        # Not a table line?
        if s[:1] != '|':
            return line
        # Add a row
        if rowClosed:
            ssCell = [cell.strip() for cell in s.split('|')[1:-1]]
        else:
            ssCell = [cell.strip() for cell in s.split('|')[1:]]
        if ssCell:
            self.rows.append(ssCell)
        self.lastRowClosed = rowClosed
        return None

    def flush(self, doc, symsGlobal, symsLocal):
        if not self.rows:
            return
        # Headers
        rows = self.rows
        if self.rows[0][0][:1] == '!':
            headers = []
            for header in rows[0]:
                s = header.strip()
                if s[:1] == '!':
                    s = s[1:]
                headers.append(expandString(s, symsGlobal, symsLocal))
            rows = rows[1:]
            nodeTable = doc.factory(form = 'table', headers = headers)
        else:
            nodeTable = doc.factory(form = 'table')
        doc.sections[-1].add(nodeTable)
        # Rows
        for row in rows:
            nodeRow = doc.factory(form = 'row')
            nodeTable.add(nodeRow)
            for cell in row:
                nodeRow.add(parseString(cell, doc, symsGlobal, symsLocal, False, form = 'cell'))
        self.rows = []

    def __str__(self):
        return 'Table(%d rows)' % len(self.rows)

#===============================================================================

class Parser(object):

    class Document(object):
        def __init__(self, factory):
            self.factory = factory
            self.clear()
        def clear(self):
            self.sections = []

    '''Builds object tree using callable factory provided based on simplistic
    parsing of structured text.  Attributes passed to factory call happen to
    align with Cmdo doc node attributes.  But it can be used independently, as
    long as attributes/values like form=list, heading=<text>, etc. are handled.
    Factory-generated objects must support an add() method.'''

    # factory is a callable object that creates items given a set of properties
    def __init__(self, factory, symsGlobal):
        self.doc        = Parser.Document(factory)
        self.symsGlobal = symsGlobal    # Global symbol dictionary for [[...]] eval
        self.symsLocal  = {}            # Local symbol dictionary for [[...]] eval
        self.block      = None

    def take(self):
        top = self.doc.sections[0]
        self.doc.clear()
        self.block = None
        return top

    def parse(self, text, sectionTop = None):
        # Always start with a top section, either provided by the caller or
        # created here.
        if sectionTop is None:
            sectionTop = self.doc.factory()
        self.doc.sections = [sectionTop]
        for line in text.split('\n'):
            while line is not None:
                if self.block is None:
                    for clsBlock in [
                            ExecBlock,
                            PlaintextBlock,
                            HeadingBlock,
                            ListBlock,
                            TableBlock,
                            TextBlock
                        ]:
                        self.block = clsBlock.start(line)
                        if self.block is not None:
                            break
                    assert self.block is not None
                    line = None
                else:
                    line = self.block.parse(line)
                    if line is not None:
                        self.block.flush(self.doc, self.symsGlobal, self.symsLocal)
                        self.block = None
        if self.block is not None:
            self.block.flush(self.doc, self.symsGlobal, self.symsLocal)
        self.block = None

#===============================================================================

def parseString(sRaw, doc, symsGlobal, symsLocal, preserveWhitespace, **props):
    '''Parse a string to expand macros and extract text and URLs.  Return a
    node tree containing with the data and a root node containing the
    properties provided.'''
    protonodes = []
    for t in _iterStringContents(sRaw, symsGlobal, symsLocal):
        if len(t) == 1:
            if preserveWhitespace or not t[0].isspace():
                protonodes.append({'text': t[0]})
        elif t[0] == '[[':
            if t[1]:
                text = t[1]
            else:
                text = t[2]
            protonodes.append({'form': 'link', 'url': t[2], 'text': text})
    if len(protonodes) == 1 and 'form' not in protonodes[0]:
        if props:
            protonodes[0].update(props)
        return doc.factory(**protonodes[0])
    nodeRoot = doc.factory(**props)
    for protonode in protonodes:
        nodeRoot.add(doc.factory(**protonode))
    return nodeRoot

def expandString(sRaw, symsGlobal, symsLocal):
    '''Parse a string to expand macros and extract text and URLs.  Flatten and
    return a single string.'''
    sOut = ''
    for t in _iterStringContents(sRaw, symsGlobal, symsLocal):
        if len(t) == 1:
            sOut += t[0]
        elif t[0] == '[[':
            if t[1]:
                sOut += t[1]
            else:
                sOut += t[2]
    return sOut

def _parseLine(s):
    cLead      = ''
    nLevel     = 0
    sRemainder = ''
    style      = None
    for i in range(len(s)):
        if cLead and s[i] == cLead:
            nLevel += 1
        elif not cLead and s[i] in '!*#|{}\'"':
            cLead = s[i]
            nLevel += 1
            if cLead == '*':
                style = 'bullet'
            elif cLead == '#':
                style = 'number'
        elif s[i].isspace():
            pass
        else:
            sRemainder = s[i:]
            break
    if not cLead and not sRemainder:
        sRemainder = s
    return (cLead * nLevel, style, sRemainder)

def _evalMacro(sMacro, symsGlobal, symsLocal):
    try:
        return str(eval(sMacro, symsGlobal, symsLocal))
    except Exception, e:
        return '{{ERROR %s in "{{%s}}"' % (str(e), sMacro)

def _iterStringParts(sIn, reChop):
    iPos = 0
    for m in reChop.finditer(sIn):
        yield (sIn[iPos:m.start()], m)
        iPos = m.end()
    if iPos < len(sIn):
        yield (sIn[iPos:], None)

def _evalMacros(sIn, symsGlobal, symsLocal):
    if not sIn:
        return ''
    sOut = ''
    for (s, m) in _iterStringParts(sIn, reEval):
        sOut += s
        if m:
            sOut += _evalMacro(m.group(2), symsGlobal, symsLocal)
    return sOut

def _iterStringContents(sIn, symsGlobal, symsLocal):
    '''Iterates a string looking for imbedded blocks and yields string tuples.
    Simple text is a tuple with length 1.  Parsed blocks, like links, are
    longer tuples providing all necessary information for complete
    interpretation.  All macros in strings are evaluated before returning.'''
    iPos = 0
    sOut = ''
    while iPos < len(sIn):
        if iPos == 0 or (mEval is not None and mEval.start() < iPos):
            mEval = reEval.search(sIn, iPos)
        if iPos == 0 or (mLink is not None and mLink.start() < iPos):
            mLink = reLink.search(sIn, iPos)
        if mEval is not None and (mLink is None or mEval.start() < mLink.start()):
            sOut += sIn[iPos:mEval.start()]
            sOut += _evalMacro(mEval.group(2), symsGlobal, symsLocal)
            iPos = mEval.end()
        elif mLink is not None:
            sOut += sIn[iPos:mLink.start()]
            if sOut:
                t = tuple([sOut])
                yield t
                sOut = ''
            t = tuple([_evalMacros(g, symsGlobal, symsLocal) for g in mLink.groups()])
            yield t
            iPos = mLink.end()
        else:
            sOut += sIn[iPos:]
            iPos = len(sIn)
    if sOut:
        t = tuple([sOut])
        yield t

#===============================================================================
# Testing
#===============================================================================

import sys

reSymbol = re.compile('\{\{(.*)\}\}')

class Node(object):
    def __init__(self, *args, **kwargs):
        self.sub = list(args)
        self.kwargs = kwargs
    def add(self, node):
        self.sub.append(node)

class Factory(object):
    def __call__(self, **kwargs):
        return Node(**kwargs)

def dump(node, level):
    keys = node.kwargs.keys()
    keys.sort()
    sys.stdout.write('%s{' % ('  ' * level))
    for key in keys:
        if key != keys[0]:
            sys.stdout.write(', ')
        v = node.kwargs[key]
        if len(v) > 60 or v.find('\n') >= 0:
            lines = v.split('\n')
            if len(lines) == 1:
                v = '%s...%s' % (v[:37], v[-20:])
            else:
                v = '%s...(%d)...%s' % (lines[0][:30], len(lines), lines[-1][-20:])
        sys.stdout.write('%s="%s"' % (key, v))
    sys.stdout.write('}\n')
    for sub in node.sub:
        dump(sub, level + 1)

class Symbol(dict):
    def __getattr__(self, name):
        return self[name]

def getEvalSymbols(s):
    root = Symbol()
    for line in s.split('\n'):
        for m in reSymbol.finditer(line):
            names = m.group(1).split('.')
            o = root
            for name in names[:-1]:
                if name not in o:
                    o[name] = Symbol()
                o = o[name]
            o[names[-1]] = '?%s?' % '.'.join(names)
    return root

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        s = open(arg).read()
        parser = Parser(Factory(), getEvalSymbols(s))
        print '\n====== %s ======' % arg
        parser.parse(s)
        node = parser.take()
        dump(node, 0)
