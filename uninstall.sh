#!/usr/bin/env python

import sys
import os, os.path

def abort(msg):
    sys.stderr.write('ERROR: %s\n<abort>\n' % msg)
    sys.exit(1)

pathCmdo = os.popen('which cmdo').read().strip()
if not pathCmdo:
    abort('cmdo not found in path')

dirPrefix = os.path.split(os.path.split(pathCmdo)[0])[0]

dirsCheck = [
    os.path.join(dirPrefix, 'lib', 'python2.4', 'site-packages', 'cmdo'),
    os.path.join(dirPrefix, 'lib', 'python2.5', 'site-packages', 'cmdo'),
    os.path.join(dirPrefix, 'lib', 'python2.6', 'site-packages', 'cmdo'),
    os.path.join(dirPrefix, 'lib', 'python2.4', 'site-packages', 'ardo'),
    os.path.join(dirPrefix, 'lib', 'python2.5', 'site-packages', 'ardo'),
    os.path.join(dirPrefix, 'lib', 'python2.6', 'site-packages', 'ardo'),
    os.path.join(dirPrefix, 'share', 'cmdo'),
    os.path.join(dirPrefix, 'share', 'ardo'),
    os.path.join(dirPrefix, 'share', 'doc', 'cmdo'),
    os.path.join(dirPrefix, 'share', 'doc', 'ardo'),
]

filesCheck = [
    os.path.join(dirPrefix, 'bin', 'cmdo'),
    os.path.join(dirPrefix, 'bin', 'ardo'),
    '/etc/bash_completion.d/cmdo',
    '/etc/bash_completion.d/ardo',
]

files = [file for file in filesCheck if os.path.isfile(file)]
dirs  = [dir for dir in dirsCheck if os.path.isdir(dir)]

print '''
************************************************************
 WARNING:
 This is a "brutal" uninstall and requires root privileges.
************************************************************

It will completely wipe the following files and directories:
'''
for file in files:
    print file
for dir in dirs:
    print '%s/' % dir
sys.stdout.write('''
Type "yes" to continue: ''')
response = sys.stdin.readline().strip().lower()
if response != 'yes':
    abort('Not performing uninstall.')

for file in files:
    os.system('sudo rm -fv "%s"' % file)
for dir in dirs:
    os.system('sudo rm -rfv "%s"' % dir)
