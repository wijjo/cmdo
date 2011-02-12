#===============================================================================
#===============================================================================
# Logging support
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
import traceback

maxTracebackLines = 32
maxWidth = 100

class ExcQuit(Exception):
    '''Application termination exception'''
    pass

#===============================================================================

def block(label, indent, border, *msgs):
    '''Display message(s) with label, border and indentation.'''
    if border:
        width = min(maxWidth, max([len(msg) for msg in msgs]) + (len(indent) * len(msgs)))
        sborder = border * width
        sys.stdout.write('%s\n' % sborder)
    if label:
        prefix = '%s: ' % label
    else:
        prefix = ''
    for i in range(len(msgs)):
        msg = msgs[i]
        while msg:
            s = msg[:(maxWidth - len(prefix) - (len(indent) * i))]
            if len(s) < len(msg):
                try:
                    s = s[:s.rindex(' ')]
                except:
                    pass
            sys.stdout.write('%s%s%s\n' % (prefix, indent * i, s))
            msg = msg[len(s):].lstrip()
        if prefix and i == 0:
            prefix = '%s: ' % ('+' * len(label))
    if border:
        sys.stdout.write('%s\n' % sborder)

#===============================================================================

def message(label, indent, *msgs):
    '''Display message(s) with label and indentation.'''
    if label:
        prefix = '%s: ' % label
    else:
        prefix = ''
    for i in range(len(msgs)):
        sys.stdout.write('%s%s%s\n' % (prefix, indent * i, msgs[i]))
        if prefix and i == 0:
            prefix = '%s: ' % ('+' * len(label))

#===============================================================================

def quit(*msgs):
    '''Display message(s) and quit (normally)'''
    message('', '', *msgs)
    message('', '<QUIT>')
    raise ExcQuit()

#===============================================================================

def abort(*msgs):
    '''Display error message(s) and quit (violently)'''
    message('ERROR', ' ', *msgs)
    message('', '', '<ABORT>')
    sys.exit(1)

#===============================================================================

def error(*msgs):
    '''Display error message(s)'''
    block('', ' ', '*', '::ERROR::', *msgs)

#===============================================================================

def warning(*msgs):
    '''Display warning message(s)'''
    message('WARNING', ' ', *msgs)

#===============================================================================

def info(*msgs):
    '''Display message(s)'''
    message('', '', *msgs)

#===============================================================================

def prompt(pmsg, isvalid = None, fixer = None, msgs = []):
    '''Display message(s) and request response.'''
    if msgs:
        message('', '', *msgs)
    answer = None
    while answer is None or (isvalid and not isvalid(answer)):
        sys.stdout.write(pmsg)
        try:
            answer = sys.stdin.readline().strip()
            if fixer:
                answer = fixer(answer)
        except KeyboardInterrupt:
            sys.stdout.write('\n')
            abort('Keyboard interrupt')
    return answer

#===============================================================================

def confirm(*msgs):
    '''Display message(s) and return True if user said "yes".'''
    answer = prompt('Continue? (y/n) ',
                    isvalid = lambda s: s == 'y' or s == 'yes' or s == 'n' or s == 'no',
                    fixer   = lambda s: s.lower(),
                    msgs    = msgs)
    return (answer == 'y' or answer == 'yes')

#===============================================================================

def _tracebackException(msg, e, skipTop, skipBottom, showException):
    msgs = [msg]
    if showException:
        msgs.append('Exception: %s' % e.__class__.__name__)
    msgs.extend(str(e).split('\n'))
    error(*msgs)
    (t, v, tb) = sys.exc_info()
    if tb is None:
        traceback.print_ext()
    nDumped = 0
    bline = '-' * 60
    tbOut = traceback.extract_tb(tb)
    if skipTop:
        tbOut = tbOut[skipTop:]
    if skipBottom:
        tbOut = tbOut[:-skipBottom]
    for (pathFile, numLine, nameFunc, text) in tbOut:
        if nDumped == maxTracebackLines:
            info('%s----- traceback truncated -----' % ('  ' * nDumped))
            break
        if pathFile == '<string>':
            s = 'line %d:' % numLine
        else:
            s = '%s:%d' % (os.path.split(pathFile)[1], numLine)
        if nameFunc and nameFunc != '?':
            s += ' %s()' % nameFunc
        if text:
            s += ' "%s"' % text
        if nDumped == 0:
            info(bline)
        sOut = '%s%s' % ('  ' * nDumped, s)
        if len(sOut) > maxWidth:
            if text:
                sOut = '%s..."' % sOut[:maxWidth-1]
            else:
                sOut = '%s...' % sOut[:maxWidth]
        info(sOut)
        nDumped += 1
    if nDumped > 0:
        info(bline)
    del tb
