#===============================================================================
#===============================================================================
# publish_text - text documentation generator for Cmdo
#
# Text publisher (simplistic)
#
# Note: You will probably get better results by publishing as HTML and then
#       filtering through lynx or w3m, i.e. using the -dump option.
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

import sys
import math
import inspect
import text_utility
from urlparse import urlparse

#===============================================================================
# Tunable style parameters
#===============================================================================

class Frame(object):
    def __init__(self, tl, t, tr, l, r, bl, b, br):
        self.tl = tl
        self.t  = t
        self.tr = tr
        self.l  = l
        self.r  = r
        self.bl = bl
        self.b  = b
        self.br = br
        if (self.tl or self.tr) and not self.t:
            self.t = ' '
        if (self.bl or self.br) and not self.b:
            self.b = ' '
    def build(self, sIn):
        sm  = self.l + sIn + self.r
        ntc = len(sm) - (len(self.tl) + len(self.tr))
        nbc = len(sm) - (len(self.bl) + len(self.br))
        st  = self.tl
        if self.t and ntc > 0:
            st += ((self.t * ((ntc + len(self.t) - 1) / len(self.t)))[:ntc])
        st += self.tr
        sb  = self.bl
        if self.b and nbc > 0:
            sb += ((self.b * ((nbc + len(self.b) - 1) / len(self.b)))[:nbc])
        sb += self.br
        sOut = st
        if sOut:
            sOut += '\n'
        sOut += sm
        if sb:
            sOut += '\n'
            sOut += sb
        return sOut

# Heading frames.  Last one is used if level >= length of list.
framesHeading = [
    Frame('+', '=', '+', '| ', ' |', '+', '=', '+'),
    Frame('' , '-', '' , ' ' , ' ' , '' , '-', '' ),
    Frame('' , '' , '' , ''  , ''  , '' , '-', '' ),
    Frame('' , '' , '' , '= ', ' =', '' , '' , '' ),
]

# How numbered list items are prefixed.
# This format gets processed twice, first time with the max # of digits
formatNumberedItem = '%%%dd: '

# What precedes a bullet list item
prefixBullet = '* '

# Indent size in characters
widthIndent = 2

# The block forms/types that produce text chunks that are accumulated until
# flushed by other block forms/types.
formsText = ['text', 'link']

# The string to repeat for table borders
borderTable = '- '

# Max width for wrapping
maxWidth = 80

#===============================================================================

class Publisher(object):

    class Cell(object):
        def __init__(self):
            self.text = ''

    class Row(object):
        def __init__(self):
            self.cells = []
        def addCell(self):
            self.cells.append(Publisher.Cell())
        def lastCell(self):
            assert len(self.cells) > 0
            return self.cells[-1]

    class Table(object):
        def __init__(self, headers):
            self.headers = headers
            self.rows    = []
            if not self.headers:
                self.headers = []   # headers should always be a list
        def addRow(self):
            self.rows.append(Publisher.Row())
        def lastRow(self):
            assert len(self.rows) > 0
            return self.rows[-1]

    class PendingTables(object):
        def __init__(self):
            self.tables = []
        def addTable(self, headers):
            self.tables.append(Publisher.Table(headers))
        def lastTable(self):
            assert len(self.tables) > 0
            return self.tables[-1]
        def popTable(self):
            assert len(self.tables) > 0
            return self.tables.pop()

    #---------------------------------------------------------------------------

    def __init__(self):
        self.dumper       = Dumper()
        self.nNest        = 0
        self.nCur         = [0]
        self.nFlushes     = 0
        self.plaintextDoc = False
        self.types        = 'text/plain'
        self.extension    = '.txt'
        # Table data is cached in raw form before flushing as plain text
        # Handle nested tables (someday).
        self.tablesPending = Publisher.PendingTables()

    #---------------------------------------------------------------------------

    def docBegin(self, context, text, style):
        pass

    #---------------------------------------------------------------------------

    def docEnd(self, context):
        # Add final linefeed, if not all plaintext.
        if not self.plaintextDoc:
            context.write('\n')

    #---------------------------------------------------------------------------

    def nodeBegin(self, context):

        form = context.getProp('form', default = '')

        context.setCache('traceLabel', 'nodeBegin:1')

        self.nCur[self.nNest] += 1
        self.nCur.append(0)
        self.nNest += 1

        # Work from cache, not node properties
        context.cacheProp('text')
        context.cacheProp('heading')

        # Process by form
        if form == 'block':
            self.blockBegin(context)
        elif form == 'list':
            self.listBegin(context)
        elif form == 'item':
            self.itemBegin(context)
        elif form == 'table':
            self.tableBegin(context)
        elif form == 'row':
            self.rowBegin(context)
        elif form == 'cell':
            self.cellBegin(context)
        elif form == 'plaintext':
            self.plaintextBegin(context)
        elif form == 'link':
            self.linkBegin(context)
        else:
            self.otherBegin(context)

        context.setCache('traceLabel', 'nodeBegin:2')

        # Insert a gap whenever the block form changes
        formPrev = context.getCache('formPrev', level = 1)
        if formPrev != form:
            #self.trace(context, '%s=>%s' % (formPrev, form))
            if formPrev is not None:
                self.setGapBefore(context, 1)
            context.setCache('formPrev', form, level = 1)

        # Consolidate text upward, if not at a form requiring flushing.
        # Also consolidate table cell text as we go.
        if not form or form in formsText:
            if context.hasCache('text') and context.getDepth() > 1:
                self.consolidateText(context)

    #---------------------------------------------------------------------------

    def nodeEnd(self, context):

        form = context.getProp('form', default = '')

        context.setCache('traceLabel', 'nodeEnd:1')

        # Process by form
        if form == 'block':
            self.blockEnd(context)
        elif form == 'list':
            self.listEnd(context)
        elif form == 'item':
            self.itemEnd(context)
        elif form == 'table':
            self.tableEnd(context)
        elif form == 'row':
            self.rowEnd(context)
        elif form == 'cell':
            self.cellEnd(context)
        elif form == 'plaintext':
            self.plaintextEnd(context)
        elif form == 'link':
            self.linkEnd(context)
        else:
            self.otherEnd(context)

        # Flush all pending text if the current node has text ready to go
        if context.hasCache('text') or context.hasCache('heading'):
            if self.plaintextDoc and form and form != 'plaintext':
                self.plaintextDoc = False
            self.flushPending(context)

        # Flush pending bottom border
        borderBottom = context.getCache('borderBottom')
        if borderBottom:
            indent = context.getCache('indent', '', inherit = True)
            context.write('%s%s\n' % (indent, borderBottom))
            context.setCache('borderBottom', '')

        context.setCache('traceLabel', 'nodeEnd:2')

        self.nNest -= 1
        self.nCur.pop()

    #---------------------------------------------------------------------------

    def blockBegin(self, context):
        if context.hasProp('text') or context.hasProp('heading'):
            self.setGapBefore(context, 1)

    #---------------------------------------------------------------------------

    def listBegin(self, context):
        # Indent a nested list
        if context.getProp('form', level = 1) == 'item':
            context.appendCacheString('indent', ' ' * widthIndent)
        else:
            self.setGapBefore(context, 1)

    #---------------------------------------------------------------------------

    def itemBegin(self, context):
        style = context.getProp('style', inherit = True)
        if style == 'bullet':
            context.setCache('prefix', prefixBullet)
        elif style == 'number':
            nItem = context.getCache('nItem', default = 0, level = 1)
            context.setCache('nItem', nItem + 1, level = 1)
            format = formatNumberedItem % numWidth(context.getBreadth())
            context.setCache('prefix', format % (nItem + 1))

    #---------------------------------------------------------------------------

    def tableBegin(self, context):
        self.tablesPending.addTable(context.getProp('headers'))

    #---------------------------------------------------------------------------

    def rowBegin(self, context):
        self.tablesPending.lastTable().addRow()

    #---------------------------------------------------------------------------

    def cellBegin(self, context):
        self.tablesPending.lastTable().lastRow().addCell()

    #---------------------------------------------------------------------------

    def plaintextBegin(self, context):
        if self.nFlushes == 0 and not context.hasProp('heading', inherit = True):
            self.plaintextDoc = True
        else:
            context.appendCacheString('indent', ' ' * widthIndent, inherit = True)
            self.setGapBefore(context, 1)

    #---------------------------------------------------------------------------

    def linkBegin(self, context):
        url   = context.getProp('url')
        label = context.getProp('text')
        if not label:
            context.setCache('text', url)
        else:
            if urlparse(url)[0] != '':
                context.setCache('text', '%s (%s)' % (label, url))
            else:
                context.setCache('text', label)

    #---------------------------------------------------------------------------

    def otherBegin(self, context):
        pass

    #---------------------------------------------------------------------------

    def blockEnd(self, context):
        self.setGapBefore(context, 1, inherit = True)

    #---------------------------------------------------------------------------

    def listEnd(self, context):
        self.setGapBefore(context, 1, inherit = True)

    #---------------------------------------------------------------------------

    def itemEnd(self, context):
        pass

    #---------------------------------------------------------------------------

    def tableEnd(self, context):
        table  = self.tablesPending.popTable()
        indent = 1      # number of spaces before header line or row
        # First determine the maximum column widths (for headers and cells
        widths = [len(header)+2 for header in table.headers]
        for row in table.rows:
            for iCell in range(len(row.cells)):
                width = len(row.cells[iCell].text)
                if iCell >= len(widths):
                    widths.append(1)    # minimum width is 1
                if width > widths[iCell]:
                    widths[iCell] = width
        widthTotal = sum(widths)
        # If it fits build a plaintext table with columns
        if widthTotal <= maxWidth:
            sLines = []
            if table.headers:
                iPos = 0
                sLines.append('')
                for iHeader in range(len(table.headers)):
                    gap = iPos - len(sLines[-1])
                    if gap > 0:
                        sLines[-1] += (' ' * gap)
                    sLines[-1] += '-%s-' % table.headers[iHeader]
                    iPos += (widths[iHeader] + 2)
            for row in table.rows:
                iPos = 0
                sLines.append('')
                for iCell in range(len(row.cells)):
                    gap = iPos - len(sLines[-1])
                    if gap > 0:
                        sLines[-1] += (' ' * gap)
                    sLines[-1] += row.cells[iCell].text
                    iPos += (widths[iCell] + 2)
        # If it's too wide use indentation instead of columns
        else:
            sLines = []
            widthTotal = 0  # Re-calculated below
            for iHeader in range(len(table.headers)):
                sLines.append('%s-%s-' % ('  ' * iHeader, table.headers[iHeader]))
                if len(sLines[-1]) > widthTotal:
                    widthTotal = len(sLines[-1])
            for row in table.rows:
                for iCell in range(len(row.cells)):
                    sLines.append('%s%s' % ('  ' * iCell, row.cells[iCell].text))
                    if len(sLines[-1]) > widthTotal:
                        widthTotal = len(sLines[-1])
        # Generate a border
        lenBorder = (widthTotal + ((len(widths) - 1) * 2) + (2 * indent))
        border = (borderTable * (((lenBorder - 1) / len(borderTable)) + 1))[:lenBorder]
        # Make sure an alternating pattern (like "- ") doesn't look too short.
        if border[-1] == ' ':
            border += borderTable
        context.setCache('borderTop'   , border)
        context.setCache('borderBottom', border)
        context.setCache('text', '\n'.join(sLines))
        context.setCache('plaintext', True)
        context.setCache('indentInside', ' ' * indent)
        self.setGapBefore(context, 1, inherit = True)

    #---------------------------------------------------------------------------

    def rowEnd(self, context):
        pass

    #---------------------------------------------------------------------------

    def cellEnd(self, context):
        if context.hasCache('text'):
            text = context.takeCache('text').replace('\n', ' ')
            self.tablesPending.lastTable().lastRow().lastCell().text += text

    #---------------------------------------------------------------------------

    def plaintextEnd(self, context):
        pass

    #---------------------------------------------------------------------------

    def linkEnd(self, context):
        pass

    #---------------------------------------------------------------------------

    def otherEnd(self, context):
        pass

    #---------------------------------------------------------------------------

    def setGapBefore(self, context, gap, level = 0, inherit = False):
        #self.trace(context, 'setGapBefore(%d, level=%d, inherit=%s)' % (gap, level, inherit))
        gapCur = context.getCache('gapBefore', default = 0, level = level, inherit = inherit)
        if gap > gapCur:
            context.setCache('gapBefore', gap, level = level, inherit = inherit)

    #---------------------------------------------------------------------------

    # Consolidate text chunks in parent node unless this is a block that
    # flushes text (done in nodeEnd()).
    def consolidateText(self, context):
        form = context.getProp('form', level = 1, inherit = True)
        # Move the heading up
        context.consolidateCacheText('heading', '\n')
        # Consolidate text
        if form == 'plaintext':
            # Plaintext requires removal of excess whitespace before consolidation.
            text = context.getCache('text', default = '')
            text2 = '\n'.join([line for line in text_utility.textFormatPlain(text, '')])
            context.setCache('text', text2)
            context.consolidateCacheText('text', '\n\n')
        else:
            # Move normal text up
            context.consolidateCacheText('text', '\n')
        # Move the gap requirement up too
        gap = context.takeCache('gapBefore')
        if gap:
            context.setCache('gapBefore', gap, level = 1)

    #---------------------------------------------------------------------------

    def flushPending(self, context):

        # Make sure a non-plaintext document starts with at least one blank line
        depth = context.getDepth()
        if self.nFlushes == 0 and not self.plaintextDoc:
            gap = 1
        else:
            gap = 0
        self.nFlushes += 1

        # Start from the topmost node with text and work down.  There should be
        # no remaining cached text, gaps, headings or borders when done.
        for level in range(depth-1, -1, -1):

            gapCur = context.takeCache('gapBefore', default = 0, level = level)
            if gapCur > gap:
                gap = gapCur

            indent = context.getCache('indent', '', level = level, inherit = True)
            indentInside = context.getCache('indentInside', '', level = level, inherit = True)

            # Heading?
            heading = context.takeCache('heading', level = level)
            if heading:
                hdLevel = len(context.getPropsStack('heading', level = level + 1))
                frame = framesHeading[min(hdLevel, len(framesHeading) - 1)]
                if frame.t and gap < 2:
                    gap = 2
                elif gap < 1:
                    gap = 1
                self._writeln(context, gap, indent, frame.build(heading))
                gap = 1

            # Top border?
            borderTop = context.takeCache('borderTop', level = level)
            if borderTop:
                self._writeln(context, gap, indent, borderTop)
                gap = 0

            # Text?
            indent += indentInside
            text = context.takeCache('text', default = '', level = level)
            if text:
                if (context.getProp('form', level = level, inherit = True) == 'plaintext' or
                    context.getCache('plaintext')):
                    for line in text_utility.textFormatPlain(text, indent):
                        self._writeln(context, gap, '', line)
                        gap = 0
                    self.setGapBefore(context, 1, level = level, inherit = True)
                else:
                    prefix = context.getCache('prefix', default = '', level = level, inherit = True)
                    for line in text_utility.textFormatWrapped(text, indent, prefix, maxWidth):
                        self._writeln(context, gap, '', line)
                        gap = 0

    #---------------------------------------------------------------------------

    def _writeln(self, context, gap, indent, s):
        iStart = 0
        while gap > 0 and iStart < len(s):
            if s[iStart] == '\n':
                iStart += 1
            else:
                context.write('\n')
            gap -= 1
        if indent:
            context.write(indent)
        context.write(s)
        context.write('\n')

    #---------------------------------------------------------------------------

    def trace(self, context, s):
        stackLines = []
        fileName = None
        stack = inspect.stack()
        for stackItem in stack[1:]:
            if fileName is None:
                fileName = stackItem[1]
            elif fileName != stackItem[1]:
                break
            stackLines.append(stackItem[2])
        print ':::{%s(%s,%d,%d)}: %s  [stack=%s]' % (
                context.getCache('traceLabel'),
                context.getProp('form'),
                self.nNest,
                self.nCur[self.nNest-1],
                s,
                ','.join([str(n) for n in stackLines]),
        )

#===============================================================================
# Utility functions and classes
#
# May be redundant to have these here, but trying to keep this module
# independently useful without cmdo.
#===============================================================================

def numWidth(n):
    try:
        return int(math.log10(abs(n))) + 1
    except:
        return 1

class Dumper:
    @staticmethod
    def abstractDict(d):
        s = ''
        keys = d.keys()
        keys.sort()
        sep = ''
        for key in keys:
            val = d[key]
            if val is not None:
                if text_utility.isString(val):
                    sVal = '"%s' % val[:20]
                    if len(sVal) < len(val):
                        sVal += '...(%d)' % len(val)
                    sVal += '"'
                else:
                    sVal = str(val)
                s += '%s%s=%s' % (sep, key, sVal)
                if not sep:
                    sep = ' '
        if not s:
            s = '(empty)'
        return s
    def __init__(self):
        self.indent = ''
    def writeln(self, s):
        print '%s%s' % (self.indent[:-2], s)
    def dump(self, context):
        form = context.getProp('form')
        label = context.getCache('traceLabel')
        self.writeln('>>>>> %s form=%s' % (label, form))
        indent2 = ''
        for level in context.levels:
            self.writeln('%sOPTIONS: %s' % (indent2, Dumper.abstractDict(level.props)))
            self.writeln('%sCACHE..: %s' % (indent2, Dumper.abstractDict(level.cache)))
            indent2 += (' ' * widthIndent)
        self.writeln('<<<<<')
    def begin(self):
        self.indent += (' ' * widthIndent)
    def end(self):
        self.indent = self.indent[:-2]
    def message(self, s):
        self.writeln('!!!%s' % s)
