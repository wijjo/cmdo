#===============================================================================
#===============================================================================
# Commando - script support module
#
# Creates a command-line grammer based on discovering specially-decorated
# functions in the script.
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
import traceback
import re

#-------------------------------------------------------------------------------
# TODO: Settings are English-specific!  Support other languages!
#
# In theory, other European languages should just need to add punctuation
# characters to the two cPunctuation... strings below.  Non-European languages
# would need to implement another version of textFormatWrapped and a mechanism
# for selecting the correct function based on locale.  Note that this function
# is used in more than just publish_text.py.
#-------------------------------------------------------------------------------

_reWs = re.compile('[ \t\r\n]+')

# Punctuation that needs trailing blank if followed by text.  Don't attempt to
# add extra blank for perios, etc. so that we don't need to differentiate
# sentences from abbreviations.
_cPunctuationTrailingSpace = '.!?,;:)}]'
# Punctuation that needs a leading blank
_cPunctuationLeadingSpace = """'"`({[#*$"""


#===============================================================================

def isString(o):
    '''Returns True if the argument is a string type.'''
    try:
        o + ''
    except:
        return False
    else:
        return True

#===============================================================================

def _charNeedsBlankSeparator(c):
    return c.isalnum() or c in _cPunctuationLeadingSpace

def textFormatWrapped(text, indent, prefix, width):
    '''Returns word-wrapped text lines using indentation, a line prefix, and a
    maximum width.  Arguments are (text, indent, prefix, width).'''
    line = '%s%s' % (indent, prefix)
    lineStart = ' ' * len(line)
    words = _reWs.split(text)
    for i in range(len(words)):
        w = words[i]
        if w:
            if len(line) + len(w) >= width:
                yield line
                line = '%s%s' % (lineStart, w)
            else:
                if len(line) > len(lineStart):
                    lastChar = line[-1]
                    if _charNeedsBlankSeparator(w[0]):
                        if lastChar in _cPunctuationTrailingSpace:
                            line += ' '
                        elif _charNeedsBlankSeparator(lastChar):
                            line += ' '
                line += w
    if len(line) > len(lineStart):
        yield line

#===============================================================================

def textFormatPlain(text, indent, width = 0):
    '''Returns lines split by linefeeds, indented and wrapped to an optional
    width.  Arguments are (text, indent and width (defaults to 0).'''
    widthIndent = len(indent)
    lines = text.split('\n')
    # Determine amount to trim from left and top to make block flush
    trimLeft = sys.maxint
    nStart   = sys.maxint
    for nLine in range(len(lines)):
        line = lines[nLine]
        for i in range(min(trimLeft, len(line))):
            if not line[i].isspace():
                if i < trimLeft:
                    trimLeft = i
                if nLine < nStart:
                    nStart = nLine
                break
        if trimLeft == 0:
            break
    # Yield trimmed and indented lines with continuations for long lines.
    # Skip trailing blank lines.
    nBlankLines = 0
    for line in lines[nStart:]:
        if not line or line.isspace():
            nBlankLines += 1
        else:
            if nBlankLines > 0:
                for i in range(nBlankLines):
                    yield ''
                nBlankLines = 0
            if width > 0:
                lineText = line[trimLeft:trimLeft+width-widthIndent]
            else:
                lineText = line[trimLeft:]
            lineOut = '%s%s' % (indent, lineText)
            while len(line) > len(lineOut) + trimLeft - widthIndent:
                yield '%s\\' % lineOut
                line = line[trimLeft+width-widthIndent:]
                lineOut = '%s%s' % (indent, line[:width-widthIndent])
            yield lineOut

#===============================================================================

def sortedIter(seq):
    '''Iterates sequence object in alphabetical order.'''
    keys = [key for key in seq]
    keys.sort()
    for key in keys:
        yield key
