#===============================================================================
#===============================================================================
# System utility functions
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
import os, os.path
from glob import glob
import re
import shlex
import select
import mailcap

#===============================================================================

def findProgram(*names):
    '''Returns first occurance of program name(s) in the system path.'''
    for dir in os.environ['PATH'].split(':'):
        for name in names:
            name = os.path.join(dir, name)
            if os.path.exists(name):
                return name
    return None

#===============================================================================

class EditorViewer(object):
    def __init__(self, cmd, edit, text):
        self.cmd  = cmd
        self.edit = edit
        self.text = text
        self.prog = os.path.split(shlex.split(self.cmd)[0])[-1]
    def addCustomOption(self, pat, s):
        if self.prog and re.match(pat, self.prog) is not None:
            self.cmd = ' '.join([self.cmd, s])
    def run(self):
        if self.cmd:
            if self.text:
                os.system(self.cmd)
            else:
                spawn(self.cmd)

#===============================================================================

def _getEditorOrViewerForType(path, type, preferEdit):
    caps = mailcap.getcaps()
    alt1 = alt2 = alt3 = None
    if type in caps:
        for cap in caps[type]:
            if 'test' in cap and cap['test']:
                if os.system(cap['test']) != 0:
                    continue
            text = ('needsterminal' in cap or 'copiousoutput' in cap)
            if 'edit' in cap:
                if text:
                    if preferEdit:
                        if alt1 is None:
                            alt1 = EditorViewer(cap['edit'] % path, True, True)
                    else:
                        if alt3 is None:
                            alt3 = EditorViewer(cap['edit'] % path, True, True)
                else:
                    if preferEdit:
                        return EditorViewer(cap['edit'] % path, True, False)
                    else:
                        if alt2 is None:
                            alt2 = EditorViewer(cap['edit'] % path, True, False)
            if 'view' in cap:
                if text:
                    if preferEdit:
                        if alt3 is None:
                            alt3 = EditorViewer(cap['view'] % path, False, True)
                    else:
                        if alt1 is None:
                            alt1 = EditorViewer(cap['view'] % path, False, True)
                else:
                    if preferEdit:
                        if alt2 is None:
                            alt2 = EditorViewer(cap['view'] % path, False, False)
                    else:
                        return EditorViewer(cap['view'] % path, False, False)
    if alt1 is not None:
        return alt1
    elif alt2 is not None:
        return alt2
    elif alt3 is not None:
        return alt3
    return None

#===============================================================================

def _getEditorOrViewer(path, preferEdit, *types):
    fallbacks = []
    ev1 = ev2 = None
    for type in types:
        ev = _getEditorOrViewerForType(path, type, preferEdit)
        if ev is not None:
            if not ev.text:
                return ev
            if ev1 is None:
                ev1 = ev
        fallback = '%s/*' % type.split('/')[0]
        if fallback not in fallbacks:
            fallbacks.append(fallback)
    for type in fallback:
        ev = _getEditorOrViewerForType(path, type, preferEdit)
        if ev is not None:
            if not ev.text:
                return ev
            if ev2 is None:
                ev2 = ev
    if ev2 is None:
        return ev1
    if ev1 is None:
        return ev2
    if ev2.text:
        return ev1
    if ev1.text:
        return ev2
    return ev1

#===============================================================================

def getEditor(path, *types):
    '''Look for GUI or terminal editor or viewer.  Prefer editor and GUI, in
    that order.'''
    return _getEditorOrViewer(path, True, *types)

#===============================================================================

def getViewer(path, *types):
    '''Look for GUI or terminal viewer or editor.  Prefer viewer and GUI, in
    that order.'''
    return _getEditorOrViewer(path, False, *types)

#===============================================================================

def getTextEditor(path, lineno = None):
    editor = getEditor(path, 'text/plain')
    if lineno is not None:
        editor.addCustomOption(r'^g?vim.*', '+%d' % lineno)
    return editor

#===============================================================================

def _nVersion(path):
    try:
        return int(os.path.splitext(path)[0].split('-')[-1])
    except ValueError:
        return -1

def getVersionedPath(path, suffix):
    '''Convert path to versioned path by adding suffix and counter when
    necessary.'''
    (base, ext) = os.path.splitext(path)
    reStripVersion = re.compile('(.*)-%s(-[0-9]*)?' % suffix)
    m = reStripVersion.match(base)
    if m:
        base = m.group(1)
    path = '%s-%s%s' % (base, suffix, ext)
    if not os.path.exists(path):
        return path
    n = 1
    for chk in glob('%s-%s-[0-9]*%s' % (base, suffix, ext)):
        i = _nVersion(chk)
        if i > n:
            n = i
    suffix2 = '%s-%d' % (suffix, n+1)
    return '%s-%s%s' % (base, suffix2, ext)

#===============================================================================

def purgeVersions(path, suffix, nKeep, reverse = False):
    '''Purge file versions created by getVersionedPath.  Purge specified
    quantity in normal or reverse sequence.'''
    (base, ext) = os.path.splitext(path)
    reStripVersion = re.compile('(.*)-%s(-[0-9]*)?' % suffix)
    m = reStripVersion.match(base)
    if m:
        base = m.group(1)
    versions = [version for version in glob('%s-%s*%s' % (base, suffix, ext))]
    if reverse:
        versions.sort(cmp = lambda v1, v2: cmp(_nVersion(v2), _nVersion(v1)))
    else:
        versions.sort(cmp = lambda v1, v2: cmp(_nVersion(v1), _nVersion(v2)))
    nPurge = len(versions) - nKeep
    if nPurge > len(versions):
        nPurge = 0
    if nPurge > 0:
        for path in versions[:nPurge]:
            os.remove(path)
    return nPurge

#===============================================================================

def spawn(command):
    '''Spawns a command process.  Returns the process ID (PID).'''
    (fin, fout) = os.pipe()
    pid = os.fork()
    if pid == 0:
        # Child
        pid = os.fork()
        if pid != 0:
            os._exit(0)
        # Child of child
        os.write(fout, '%d' % os.getpid())
        try:
            a = shlex.split(command)
            os.execvp(a[0], a)
        except OSError, e:
            sys.stderr.write('Failed to spawn "%s"\n    %s\n' % (command, e))
        os._exit(1)
    else:
        ready = select.select([fin], [], [])
        os.waitpid(pid, 0)
        if ready[0] and ready[0][0] == fin:
            pid = int(os.read(fin, 99).strip())
        else:
            sys.stderr.write('Failed to get pid for "%s"\n' % command)
            pid = 0
        os.close(fin)
        os.close(fout)
        return pid

#===============================================================================

def findWriteablePathDirectory():
    for dir in os.environ['PATH'].split(':'):
        if isWriteable(dir):
            return dir
    return None
