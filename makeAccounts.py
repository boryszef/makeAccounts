#!/usr/bin/python

from sys import argv
import os
import subprocess as sp
import stat
import random
import crypt
import argparse
import re

# These are the names of backup copies that will be created

passwdBak = "/etc/passwd.mAcc"
shadowBak = "/etc/shadow.mAcc"
groupBak = "/etc/group.mAcc"
exportsBak = "/etc/exports.mAcc"

# Parse command line arguments

parser = argparse.ArgumentParser(description="Create students' accounts")
parser.add_argument('--prefix', default="stud", nargs='?', \
                    help='prefix for the logins and home directories')
parser.add_argument('--teacher', default=None, nargs='?', help='teacher\'s login')
parser.add_argument('--dry', action='store_true', \
                    help='dry run - make no changes, just simulate the behaviour')
parser.add_argument('nacc', help='number of accounts to add', type=int)
settings = parser.parse_args()

# Enforce restrictions

if not settings.prefix.isalpha():
    print "Prefix may contain only letters"
    exit(1)

# UID for different groups are off-set by 100, hence the limitation:

startUID = 0

if settings.nacc > 99:
	print "Maximum on 99 accounts allowed"
	exit(1)

# Collect used uids (in uids) and find UID/GID of the teacher
# Store existing UIDs in existing list. These are matched against
# regular expression '^prefix[0-9]+$'

passwd = open('/etc/passwd').readlines()
uids = []
exists = False
existing = []
uidMatch = re.compile('^%s[0-9]+$' % settings.prefix)
for l in passwd:
	line = l.split(':')
	uid = int(line[2])
	if uidMatch.match(line[0]):
            exists = True
            existing.append(uid)
	uids.append(uid)
        # Store only if teacher was specified (not None)
        if settings.teacher and line[0] == settings.teacher:
            teacherUID = int(line[2])
            teacherGID = int(line[3])
uids.sort()

append = False
if exists:
	print "User exist!"
        answer = raw_input("Do you want to add more accounts for this teacher? (y/n) ")
        if answer != 'y': exit(1)
        append = True
        topExisting = max(existing)
        startUID = topExisting % 100
        if startUID+settings.nacc > 99:
            print "The maximum number of accounts would be exceeded. Exiting."
            exit(1)

uid = 30000
free = False
while not free:
	uid += 100
	if not uid in uids:
		free = True
		for i in xrange(99):
			if uid+i in uids:
				free = False
				break

if append:
    UID = topExisting+1
else:
    UID = uid+1
print "The users will have UIDs starting from %d" % UID

print "Making backup %s" % passwdBak
if not settings.dry:
    sp.call(["cp", "/etc/passwd", passwdBak])
print "Adding users to passwd"
if not settings.dry:
    passwd = open('/etc/passwd', 'a')
createdAccounts = []
for i in xrange(startUID, startUID+settings.nacc):
	uname = "%s%02d" % (settings.prefix, i+1)
	group = settings.prefix
	uid = UID + i
	line = "%s:x:%d:1002::/home/%s/%s:/bin/bash" % (uname, uid, group, uname)
        if not settings.dry:
	    print >>passwd, line
        else:
	    print ">>passwd,", line
        createdAccounts.append(uname)
if not settings.dry:
    passwd.close()

chrtable = "abcdefghijklmnopqrstuvwxyz0123456789"
pwd = "".join(random.sample(chrtable, 8))
print "Random password: %s" % pwd
salt = "".join(random.sample(chrtable, 2))
hashpwd = crypt.crypt(pwd, "$6$"+salt)
print "Hash: %s" % hashpwd
if (not settings.dry) and settings.teacher:
    storePass = '/home/%s/haslo_studenckie' % settings.teacher
    savepwd = open(storePass, 'a')
    print >>savepwd, "Logins: %s%02d to %s%02d" % (settings.prefix, startUID+1, settings.prefix, startUID+settings.nacc)
    print >>savepwd, "Password:", pwd
    savepwd.close()
    os.chmod(storePass, stat.S_IRUSR | stat.S_IWUSR)
    os.chown(storePass, teacherUID, teacherGID)

print "Making backup %s" % shadowBak
if not settings.dry:
    sp.call(["cp", "/etc/shadow", shadowBak])

print "Calling pwconv"
if not settings.dry:
    sp.call(["pwconv"])

shadowOrig = open('/etc/shadow').readlines()
if not settings.dry:
    shadow = open('/etc/shadow', 'w')
for l in shadowOrig:
	l = l.rstrip()
	tmp = l.split(':')
	#if l.startswith(settings.prefix):
	if tmp[0] in createdAccounts:
		tmp[1] = hashpwd
		line = ":".join(tmp)
                if not settings.dry:
		    print >>shadow, line
	else:
                if not settings.dry:
		    print >>shadow, l

if not settings.dry:
    shadow.close()

exports = open('/etc/exports').readlines()
found = False
exportMatch = re.compile('\s*/home/%s\s+' % settings.prefix)
for l in exports:
	if exportMatch.match(l):
		found = True
		break
if found:
	print "Entry in /etc/exports exists"
else:
	print "Making backup %s" % exportsBak
        if not settings.dry:
            sp.call(["cp", "/etc/exports", exportsBak])
        if not settings.dry:
            expt = open('/etc/exports', 'a')
            print >>expt, "/home/%s\t\t192.168.1.128/25(rw,root_squash,no_subtree_check)" % settings.prefix
            expt.close()
        else:
            print ">>expt, /home/%s\t\t192.168.1.128/25(rw,root_squash,no_subtree_check)" % settings.prefix

GID = UID/100 + 1000
print "Generated GID = %d" % GID
group = open('/etc/group').readlines()
found = False
for l in group:
	tmp = l.split(':')
	g = int(tmp[2])
	if l.startswith(settings.prefix):
		if g == GID:
			print "Group exists and has correct GID"
			found = True
			break
		else:
			print "Group exists, but has an incorrect GID!"
			exit(1)
	elif g == GID:
		print "GID is already taken!"
		exit(1)
if not found:
	print "Adding group %d" % GID
	print "Making backup %s" % groupBak
        if not settings.dry:
            sp.call(["cp", "/etc/group", groupBak])
            group = open('/etc/group', 'a')
        if settings.teacher:
            if not settings.dry:
                print >>group, "%s:x:%d:%s" % (settings.prefix, GID, settings.teacher)
            else:
                print ">>group, %s:x:%d:%s" % (settings.prefix, GID, settings.teacher)
        else:
            if not settings.dry:
    	        print >>group, "%s:x:%d:" % (settings.prefix, GID)
            else:
    	        print ">>group, %s:x:%d:" % (settings.prefix, GID)
        if not settings.dry:
            group.close()

print "Creating home directories"
if (not settings.dry) and (not os.access("/home/%s" % settings.prefix, os.X_OK)):
    sp.call(["mkdir", "/home/%s" % settings.prefix])
    os.chown("/home/%s" % settings.prefix, 0, GID)
    os.chmod("/home/%s" % settings.prefix, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                                    stat.S_IRGRP | stat.S_IXGRP | stat.S_IXOTH)
else:
    print "Root for home dirs exists."

replacePersonalData = [
'.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml',
'.config/xfce4/desktop/icons.screen0-1264x928.rc',
'.config/xfce4/desktop/icons.screen0-1264x959.rc',
'.config/xfce4/desktop/icons.screen0-1264x1008.rc' ]

for i in xrange(startUID, startUID+settings.nacc):
	uname = "%s%02d" % (settings.prefix, i+1)
	name = "/home/%s/%s" % (settings.prefix, uname)
        if not settings.dry:
            sp.call(["mkdir", name])
	    sp.call(["tar", "xf", "/root/skeleton.tar", "-C", name])
            sp.call(["chown", "-R", "%s:students" % uname, name])
	    os.chmod(name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            for fnm in replacePersonalData:
                origFile = open(name+"/"+fnm).read()
                content = origFile.replace('%%REPLACEGROUP%%', settings.prefix).replace('%%REPLACEUSER%%', uname)
                newFile = open(name+"/"+fnm, "w")
                newFile.write(content)
                newFile.close()

print "Calling exportfs"
if not settings.dry:
    sp.call(["exportfs", "-a"])
