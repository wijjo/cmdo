#===============================================================================
#===============================================================================
# publish_dump - raw documentation dump generator for Cmdo
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

import cgi
import text_utility

#===============================================================================

class Publisher(object):

    #---------------------------------------------------------------------------

    def __init__(self):
        self.depth      = 0
        self.hdLevel    = 0
        self.newLine    = False
        self.plaintext  = 0
        self.pendingTOC = True
        self.types      = ('text/html', 'text/xhtml+xml')
        self.extension  = '.html'

    #---------------------------------------------------------------------------

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

    #---------------------------------------------------------------------------

    def docBegin(self, context, title, style):
        if style and style.lower() == 'small':
            self.write(context, head % (cgi.escape(title), cssSmall, cssSmallPrint))
        else:
            self.write(context, head % (cgi.escape(title), cssDefault, cssDefaultPrint))

    #---------------------------------------------------------------------------

    def docEnd(self, context):
        self.write(context, '\n</body>\n</html>')
        context.write('\n')

    #---------------------------------------------------------------------------

    def nodeBegin(self, context):
        form    = context.getProp('form', default = '')
        heading = context.getProp('heading')
        tocid   = context.getProp('tocid')
        if tocid:
            self.write(context, '<span id="%s">\n' % tocid)
        if heading:
            heading = cgi.escape(heading)
            self.hdLevel += 1
            if tocid and self.hdLevel <= 2:
                self.write(context, '<table class="h%dbar"><tr>' % self.hdLevel)
                self.write(context, '<td><h%d class="h%dbarheading">%s</h%d></td>'
                                % (self.hdLevel, self.hdLevel, heading, self.hdLevel))
                self.write(context, '<td class="h%dbartopcell">' % self.hdLevel)
                self.write(context, '<a href="#toc" class="h%dbartoplink">Top</a>' % self.hdLevel)
                self.write(context, '</td>')
                self.write(context, '</tr></table>\n')
            else:
                self.write(context, '<h%d class="heading%d">%s</h%d>\n'
                                        % (self.hdLevel, self.hdLevel, heading, self.hdLevel))
        context.cacheProp('text')
        context.setCache('newLine', True)
        if form == 'table':
            self.tableBegin(context)
        elif form == 'list':
            self.listBegin(context)
        elif form == 'item':
            self.itemBegin(context)
        elif form == 'row':
            self.rowBegin(context)
        elif form == 'cell':
            self.cellBegin(context)
        elif form == 'plaintext':
            self.plaintextBegin(context)
        elif form == 'link':
            self.linkBegin(context)
        elif form == 'block':
            self.blockBegin(context)
        elif form[:3] == 'toc':
            assert len(form) > 3
            self.tocBegin(context, int(form[3:]))
        if context.hasCache('text'):
            text = cgi.escape(context.getCache('text'))
            if self.plaintext > 0:
                context.write('\n<pre>')
                #indent = '  ' * self.depth
                indent = ''
                for line in text_utility.textFormatPlain(text, indent, 80):
                    context.write('\n')
                    context.write(line)
                context.write('</pre>\n')
            else:
                if context.getCache('newLine', default = True):
                    indent = '  ' * self.depth
                    for line in text_utility.textFormatWrapped(text, indent, '', 80):
                        context.write('\n')
                        context.write(line)
                else:
                    context.write(text)
            context.flush()
        self.depth += 1
        if heading and self.pendingTOC:
            self.pendingTOC = False
            context.feedTOC(self)

    #---------------------------------------------------------------------------

    def nodeEnd(self, context):
        form = context.getProp('form', default = '')
        if context.getProp('heading'):
            self.hdLevel -= 1
        self.depth -= 1
        if form == 'table':
            self.tableEnd(context)
        elif form == 'list':
            self.listEnd(context)
        elif form == 'item':
            self.itemEnd(context)
        elif form == 'row':
            self.rowEnd(context)
        elif form == 'cell':
            self.cellEnd(context)
        elif form == 'plaintext':
            self.plaintextEnd(context)
        elif form == 'link':
            self.linkEnd(context)
        elif form == 'block':
            self.blockEnd(context)
        elif form[:3] == 'toc':
            assert len(form) > 3
            self.tocEnd(context, int(form[3:]))
        if context.hasProp('tocid'):
            self.write(context, '</span>\n')

    #---------------------------------------------------------------------------

    def tableBegin(self, context):
        self.write(context, '<table class="gentable">\n')
        headers = context.getProp('headers')
        if headers:
            self.depth += 1
            self.write(context, '<tr class="genrow">\n')
            self.depth += 1
            for header in headers:
                self.write(context, '<th class="genheader">%s</th>\n' % header)
            self.depth -= 1
            self.write(context, '</tr>\n')
            self.depth -= 1

    #---------------------------------------------------------------------------

    def listBegin(self, context):
        style = context.getProp('style')
        if style == 'bullet':
            self.write(context, '<ul>\n')
        elif style == 'number':
            self.write(context, '<ol>\n')
        else:
            self.write(context, '<div>\n')

    #---------------------------------------------------------------------------

    def itemBegin(self, context):
        style = context.getProp('style', inherit = True)
        if style == 'bullet':
            self.write(context, '<li>\n')
        elif style == 'number':
            self.write(context, '<li>\n')
        else:
            self.write(context, '<div>\n')

    #---------------------------------------------------------------------------

    def rowBegin(self, context):
        self.write(context, '<tr>\n')

    #---------------------------------------------------------------------------

    def cellBegin(self, context):
        self.write(context, '<td class="gencell">\n')

    #---------------------------------------------------------------------------

    def plaintextBegin(self, context):
        self.plaintext += 1

    #---------------------------------------------------------------------------

    def linkBegin(self, context):
        url = context.getProp('url')
        self.write(context, '<a href="%s">' % url)
        if not context.hasCache('text'):
            context.setCache('text', url)
        context.setCache('newLine', False)

    #---------------------------------------------------------------------------

    def blockBegin(self, context):
        self.write(context, '<div class="block">\n')

    #---------------------------------------------------------------------------

    def tocBegin(self, context, level):
        if level == 0:
            self.write(context, '<div id="toc" class="tocblock">\n')
        else:
            self.write(context, '<div class="toc%d">' % level)
            if context.hasProp('toclink'):
                self.write(context, '<a href=#%s>%s</a>' % (
                                cgi.escape(context.getProp('toclink')),
                                cgi.escape(context.getProp('tocheading'))))
            else:
                self.write(context, cgi.escape(context.getProp('tocheading')))
            self.write(context, '</div>\n')

    #---------------------------------------------------------------------------

    def tableEnd(self, context):
        self.write(context, '</table>\n')

    #---------------------------------------------------------------------------

    def listEnd(self, context):
        style = context.getProp('style')
        if style == 'bullet':
            self.write(context, '</ul>\n')
        elif style == 'number':
            self.write(context, '</ol>\n')
        else:
            self.write(context, '</div>\n')

    #---------------------------------------------------------------------------

    def itemEnd(self, context):
        style = context.getProp('style', inherit = True)
        if style == 'bullet':
            self.write(context, '</li>\n')
        elif style == 'number':
            self.write(context, '</li>\n')
        else:
            self.write(context, '</div>\n')

    #---------------------------------------------------------------------------

    def rowEnd(self, context):
        self.write(context, '</tr>\n')

    #---------------------------------------------------------------------------

    def cellEnd(self, context):
        self.write(context, '</td>\n')

    #---------------------------------------------------------------------------

    def plaintextEnd(self, context):
        self.plaintext -= 1

    #---------------------------------------------------------------------------

    def linkEnd(self, context):
        self.write(context, '</a>\n')

    #---------------------------------------------------------------------------

    def blockEnd(self, context):
        self.write(context, '</div>\n')

    #---------------------------------------------------------------------------

    def tocEnd(self, context, level):
        if level == 0:
            self.write(context, '</div>\n')

#===============================================================================

cssDefault = '''
* {
    font-size: 12pt;
}

.h1bar {
    background-color: #aaaaff;
    margin-top: 32px;
    margin-bottom: 12px;
    padding: 4px;
    width: 100%;
    height: auto;
    border-spacing: 0;
    border-collapse: collapse;
}

.h1barheading {
    font-size: 16pt;
    font-weight: bold;
    margin-top: 0px;
    margin-bottom: 0px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 4px;
}

.h1bartopcell {
    text-align: right;
}

.h1bartoplink {
    font-size: 11pt;
    text-indent: 1em;
    padding: 2px;
}

.h2bar {
    background-color: #e8e8ff;
    margin-top: 32px;
    margin-bottom: 12px;
    padding: 2px;
    width: 100%;
    height: auto;
    border-spacing: 0;
    border-collapse: collapse;
}

.h2barheading {
    font-size: 14pt;
    font-weight: bold;
    margin-top: 0px;
    margin-bottom: 0px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 2px;
}

.h2bartopcell {
    text-align: right;
}

.h2bartoplink {
    font-size: 11pt;
    text-indent: 1em;
    padding: 2px;
}

.heading1 {
    background-color: #aaaaff;
    font-size: 16pt;
    font-weight: bold;
    margin-top: 32px;
    margin-bottom: 12px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 4px;
}

.heading2 {
    background-color: #e8e8ff;
    font-size: 14pt;
    font-weight: bold;
    margin-top: 32px;
    margin-bottom: 12px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 2px;
}

.heading3 {
    border-bottom: 1px solid gray;
    width: auto;
    font-size: 13pt;
    font-weight: bold;
    margin-top: 24px;
    margin-bottom: 12px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.heading4 {
    font-size: 12pt;
    font-weight: bold;
    margin-top: 12px;
    margin-bottom: 6px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.heading5 {
    font-size: 12pt;
    font-weight: italic;
    margin-top: 8px;
    margin-bottom: 4px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.heading6 {
    font-size: 11pt;
    font-weight: italic;
    margin-top: 8px;
    margin-bottom: 4px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.gentable {
    border: 1px solid gray;
    margin-bottom: 8px;
    border-spacing: 0;
    border-collapse: collapse;
}

.genheader {
    border: 1px solid gray;
    background-color: #F2F2FF;
    padding: 2px 4px;
}

.genrow {
}

.gencell {
    border: 1px solid gray;
    padding: 2px 4px;
}

ol {
    margin-top: 0px;
    margin-bottom: 0px;
    margin-left: -8px;
    margin-right: 0px;
}

ol li {
    list-style-type: decimal;
}

ul li {
}

p {
    margin-top: 4px;
    margin-bottom: 4px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

pre {
    background-color: #eeeeee;
    font-size: 10pt;
}

.tocblock {
    border: 1px solid gray;
    background-color: #eeeeff;
    padding: 10px;
    margin: 20px;
}

.toc0 {
}

.toc1 {
    padding-top: 10px;
    font-weight: bold;
}

.toc2 {
    padding-left: 16px;
}

.toc3 {
    padding-left: 32px;
}

.toc4 {
    padding-left: 48px;
}

.block {
    padding-top: 6px;
    padding-bottom: 6px;
}
'''

cssDefaultPrint = '''
.h1bartoplink {
    display: none;
}

.h2bartoplink {
    display: none;
}

.tocblock {
    display: none;
}

'''

cssSmall = '''
* {
    font-size: 10pt;
}

.h1bar {
    background-color: #aaaaff;
    margin-top: 32px;
    margin-bottom: 12px;
    padding: 4px;
    width: 100%;
    height: auto;
    border-spacing: 0;
    border-collapse: collapse;
}

.h1barheading {
    font-size: 14pt;
    font-weight: bold;
    margin-top: 0px;
    margin-bottom: 0px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 4px;
}

.h1bartopcell {
    text-align: right;
}

.h1bartoplink {
    font-size: 9pt;
    text-indent: 1em;
    padding: 2px;
}

.h2bar {
    background-color: #e8e8ff;
    margin-top: 32px;
    margin-bottom: 12px;
    padding: 2px;
    width: 100%;
    height: auto;
    border-spacing: 0;
    border-collapse: collapse;
}

.h2barheading {
    font-size: 12pt;
    font-weight: bold;
    margin-top: 0px;
    margin-bottom: 0px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 2px;
}

.h2bartopcell {
    text-align: right;
}

.h2bartoplink {
    font-size: 9pt;
    text-indent: 1em;
    padding: 2px;
}

.heading1 {
    background-color: #aaaaff;
    font-size: 14pt;
    font-weight: bold;
    margin-top: 32px;
    margin-bottom: 12px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 4px;
}

.heading2 {
    background-color: #e8e8ff;
    font-size: 12pt;
    font-weight: bold;
    margin-top: 32px;
    margin-bottom: 12px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 2px;
}

.heading3 {
    border-bottom: 1px solid gray;
    width: auto;
    font-size: 11pt;
    font-weight: bold;
    margin-top: 24px;
    margin-bottom: 12px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.heading4 {
    font-size: 10pt;
    font-weight: bold;
    margin-top: 12px;
    margin-bottom: 6px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.heading5 {
    font-size: 10pt;
    font-weight: italic;
    margin-top: 8px;
    margin-bottom: 4px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.heading6 {
    font-size: 9pt;
    font-weight: italic;
    margin-top: 8px;
    margin-bottom: 4px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

.gentable {
    border: 1px solid gray;
    margin-bottom: 8px;
    border-spacing: 0;
    border-collapse: collapse;
}

.genheader {
    border: 1px solid gray;
    background-color: #F2F2FF;
    padding: 2px 4px;
}

.genrow {
}

.gencell {
    border: 1px solid gray;
    padding: 2px 4px;
}

ol {
    margin-top: 0px;
    margin-bottom: 0px;
    margin-left: -8px;
    margin-right: 0px;
}

ol li {
    list-style-type: decimal;
}

ul li {
}

p {
    margin-top: 4px;
    margin-bottom: 4px;
    margin-left: 0px;
    margin-right: 0px;
    padding: 0;
}

pre {
    background-color: #eeeeee;
    font-size: 9pt;
}

.tocblock {
    border: 1px solid gray;
    background-color: #eeeeff;
    padding: 10px;
    margin: 20px;
}

.toc0 {
}

.toc1 {
    padding-top: 10px;
    font-weight: bold;
}

.toc2 {
    padding-left: 16px;
}

.toc3 {
    padding-left: 32px;
}

.toc4 {
    padding-left: 48px;
}

.block {
    padding-top: 6px;
    padding-bottom: 6px;
}
'''

cssSmallPrint = '''
.h1bartoplink {
    display: none;
}

.h2bartoplink {
    display: none;
}

.tocblock {
    display: none;
}

'''

head = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>

<meta http-equiv="content-type" content="text/html;charset=utf-8" />

<title>%s</title>

<style type="text/css">%s</style>

<style type="text/css" media="print">%s</style>

</head>

<body>

'''
