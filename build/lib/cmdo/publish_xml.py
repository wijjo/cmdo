#===============================================================================
#===============================================================================
# publish_xml - xml documentation generator for Cmdo
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
from xml.sax import saxutils
import text_utility

# Orders the important properties.  Properties not specified here trail and are
# sorted alphabetically.  ( see cmpProp() )
propOrder = ['form', 'heading', 'text']

#===============================================================================

class Publisher(object):

    def __init__(self):
        self.depth     = 0
        self.newLine   = False
        self.types     = ('text/xml', 'text/xhtml+xml', 'text/html')
        self.extension = '.xml'

    def docBegin(self, context, title, style):
        self.write(context, '<?xml version="1.0" encoding="UTF-8"?>\n')

    def docEnd(self, context):
        self.write(context, '')

    def write(self, context, *chunks):
        for chunk in chunks:
            chunk = str(chunk)
            newLine = self.newLine
            self.newLine = (len(chunk) > 0 and chunk[-1] == '\n')
            if self.newLine:
                chunk = chunk[:-1]
            lines = chunk.split('\n')
            for i in range(len(lines)):
                line = lines[i]
                if newLine:
                    context.write('\n')
                    context.write('  ' * self.depth)
                else:
                    newLine = True
                context.write(line)
        context.flush()

    def nodeBegin(self, context):
        self.write(context, '<node')
        props = context.getAllProps()
        keys = props.keys()
        keys.sort(cmpProp)
        for key in keys:
            if key != 'text':
                self.write(context, ' %s=%s' % (key, saxutils.quoteattr(str(props[key]))))
        if context.getBreadth() == 0 and not context.hasProp('text'):
            self.write(context, '/>\n')
        else:
            self.write(context, '>\n')
        text = context.getProp('text')
        self.depth += 1
        if text:
            indent = '  ' * self.depth
            for line in text_utility.textFormatPlain(saxutils.escape(text), indent):
                context.write('\n')
                context.write(line)

    def nodeEnd(self, context):
        self.depth -= 1
        if context.getBreadth() > 0 or context.hasProp('text'):
            self.write(context, '</node>\n')

def cmpProp(o1, o2):
    try:
        i1 = propOrder.index(o1)
    except:
        i1 = sys.maxint
    try:
        i2 = propOrder.index(o2)
    except:
        i2 = sys.maxint
    if i1 != i2:
        return cmp(i1, i2)
    return cmp(o1, o2)
