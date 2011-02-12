#!/usr/bin/env python

"""Setup script for the cmdo (commando) module distribution."""

import os, os.path
from glob import glob
from distutils.core import setup, Command
from distutils.command.install import install

version = os.popen('test/cmdo version').readline().strip().split(' ')[1]
print 'version=%s' % version

class generate(Command):
    description = "Generate documentation"
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        os.system('test/cmdo help development output=DEVELOPMENT')
        os.system('test/cmdo help readme output=README')
        os.system('test/cmdo help install output=INSTALL')
        os.system('test/cmdo help reference output=REFERENCE')
        os.system('test/cmdo help development format=html output=development.html')
        os.system('test/cmdo help readme format=html output=readme.html')
        os.system('test/cmdo help install format=html output=install.html')
        os.system('test/cmdo help reference format=html output=reference.html')
        os.system('test/cmdo help bash_completion_script output=etc/bash_completion.d/cmdo plain="yes"')
        os.system('test/ardo help bash_completion_script output=etc/bash_completion.d/ardo plain="yes"')

install.sub_commands.append(('generate', None))

setup(
    name = 'cmdo',
    version = version,
    description = 'Create command-driven scripts with smart arguments and help derived from decorated functions.',
    long_description = '''
Cmdo
====

Simplifies construction of command-based tools.  Tool development consists of:

* Creating module files in one of several known locations using special file
  extensions.
* Writing ordinary Python functions.
* Adding decorators to choose exported functions and to describe argument
  types/repetition/defaults.
* Creating new argument type classes as needed.
* Adding descriptive documentation as structured text in doc strings,
  decorators, and or separate documentation modules.

Benefits include:

* Full command line interpretation, including support for both user-friendly
  simplified syntax and developer-friendly Python expressions.
* Argument type and quantity checking.
* Argument validation, conversion and defaults.
* Keyword assignment for optional arguments.
* Automatic support for simple bash shell command line completion.
* Command line help for modules, functions and other documentation.
* Publish help to pretty text, HTML, XML, or custom format.
* View help in browser or other viewer based on mime type.
* On-demand module loading.
* Import-less inter-module calling and references through special CMDO
  namespace.
* Complete support for all normal Python capabilities.
* Error handling, logging, traceback, etc.
''',
    author = 'Steve Cooper',
    author_email = "steve@wijjo.com",
    url = "http://wijjo.com/project/?c=cmdo",
    download_url = "http://wijjo.com/files/cmdo-%s.tar.gz" % version,
    license = 'GPL2',
    platforms = ['Linux'],
    packages = ['cmdo'],
    scripts = ['bin/cmdo', 'bin/ardo'],
    data_files = [
        ('lib/cmdo/cmdo.d', glob(os.path.join('cmdo.d', '*.cmdo'))),
        ('lib/cmdo/cmdo.d', glob(os.path.join('cmdo.d', '*.cmdocore'))),
        ('lib/cmdo/cmdo.d', glob(os.path.join('cmdo.d', '*.cmdodoc'))),
        ('lib/ardo/ardo.d', glob(os.path.join('ardo.d', '*.cmdo'))),
        ('lib/ardo/ardo.d', glob(os.path.join('ardo.d', '*.cmdocore'))),
        ('lib/ardo/ardo.d', glob(os.path.join('ardo.d', '*.cmdodoc'))),
        ('/etc/bash_completion.d', glob(os.path.join('etc', 'bash_completion.d', '*'))),
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Software Development',
        'Topic :: Software Development :: Documentation',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup',
        'Topic :: Text Processing :: Markup :: HTML',
        'Topic :: Text Processing :: Markup :: XML',
        'Topic :: Utilities',
    ],
    cmdclass = {
        'generate': generate
    },
)
