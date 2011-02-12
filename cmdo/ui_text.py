#===============================================================================
#===============================================================================
# ui_text - text user interface driver for Cmdo
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

import public
import structext
from log_utility import *

class Driver(object):

    class Prompter(object):
        def __init__(self, name):
            self.name = name
        def help(self):
            public.execute('help %s' % self.name)
        def ask(self, desc, descDef, funcGet, optional):
            while True:
                msgs = []
                msgs.append('\n=== %s' % (desc))
                if optional:
                    msgs.append('(optional)')
                if descDef:
                    msgs.append('(default = %s)' % descDef)
                msgs.append('(? for help)')
                answer = prompt('> ', msgs = msgs)
                if answer == '?':
                    self.help()
                    answer = None
                elif funcGet:
                    try:
                        if not answer:
                            answer = None
                        answer = funcGet(answer)
                    except public.ExcBase, e:
                        if not optional:
                            error(str(e))
                        answer = None
                if answer or optional:
                    return answer

    def promptArgs(self, func, args, kwargs):
        info('\n:: %s ::' % func.name)
        prompter = Driver.Prompter(func.name)
        for t in func.defs:
            args.append(prompter.ask(t.desc, t.descDef, t.get, False))
        if func.more:
            i = 0
            while i < func.more.countMax:
                optional = i >= func.more.countMin
                answer = prompter.ask(func.more.desc, None, func.more.get, optional)
                if answer is None:
                    break
                args.append(answer)
                i += 1
        kws = func.kwdefs.keys()
        kws.sort()
        for kw in kws:
            if kw not in kwargs:
                t = func.kwdefs[kw]
                answer = prompter.ask(t.desc, t.descDef, t.get, True)
                if answer is not None:
                    kwargs[kw] = answer
