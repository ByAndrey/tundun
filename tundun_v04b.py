#!/usr/bin/python3

from pexpect import pxssh
import re
import json
import os

import getopt
import sys

# Get the arguments from the command-line
argv = sys.argv[1:]
ip=0
dir='./'
restart=False
visual=False
mode=''

try:
   opts, args = getopt.getopt(argv, 'i:u:p:crv',["ip,","user","password","conf.d","restart"])
   for opt, arg in opts:
     if (opt=='-i' or opt=='--ip'):
        ip=arg
     if (opt=='-u' or opt=='--user'):
        username=arg
     if (opt=='-p' or opt=='--password'):
        password=arg
     if (opt=='-c' or opt=='--conf.d'):
        dir='/etc/multipath/conf.d'
     if (opt=='-r' or opt=='--restart'):
        restart=True
     if (opt=='-v'):
        visual=True

except getopt.GetoptError:
   print ('Usage: %s -i <Storage management ip> -u <username> -p <password>'%sys.argv[0])
   print ('Options:')
   print ('   -c create luns.conf file in /etc/multipath/conf.d/')
   print ('   -r restart multipathd service')
   sys.exit(2)

if (not(ip) or not(username) or not(password)):
   print ('Usage: %s -i <Storage management ip> -u <username> -p <password>'%sys.argv[0])
   print ('Options:')
   print ('   -c create luns.conf file in /etc/multipath/conf.d/')
   print ('   -r restart multipathd service')
   sys.exit(2)

def get_luninfo(address,username,password):
   global mode
   s = pxssh.pxssh(echo=False)
   try:
      s.login(address,username,password)
      print("SSH connection established")
   except:
      print("Cannot connect to %s"%address)
      sys.exit(2)
   s.sendline("tatlin-cli --json resource show block")
   s.prompt()
   if (str(s.before).find("wwid") != -1):
      mode="tatlin_u"
      block = json.loads(s.before.rstrip().decode('utf-8'))
   else:
      s.sendline("lsvdisk -json")
      s.prompt()
      if (str(s.before).find("vdisk_UID") != -1):
         mode="cx1"
         block = json.loads(s.before.rstrip().decode('utf-8'))
      else:
         print("Unable to get LUN information. Unknown storage system")
         sys.exit(2)
   s.logout()
   s.close()
   return(block)

data = (get_luninfo(ip,username,password))

if (dir!="./"):
   os.system("mkdir -p %s"%dir)
file = open("%s/luns_%s.conf"%(dir,ip.split('.')[-1]),"w+")

if (mode=="tatlin_u"):
   
   if visual:
      print("multipaths {")
   file.write("multipaths {\n")
   for lun in data:
      if visual: 
         print("   multipath {")
         print("      wwid 3%s"%(lun['wwid'][4:].lower()))
         print("      alias %s"%(lun['name']))
         print("   }")
      file.write("   multipath {\n")
      file.write("      wwid 3%s\n"%(lun['wwid'][4:].lower()))
      file.write("      alias %s\n"%(lun['name']))
      file.write("   }\n")
   if visual:
      print("}")
   file.write("}")

if (mode=="cx1"):

   if visual:
      print("multipaths {")
   file.write("multipaths {\n")
   for lun in data:
      if visual:
         print("   multipath {")
         print("      wwid 3%s"%(lun['vdisk_UID'].lower()))
         print("      alias %s"%(lun['name']))
         print("   }")
      file.write("   multipath {\n")
      file.write("      wwid 3%s\n"%(lun['vdisk_UID'].lower()))
      file.write("      alias %s\n"%(lun['name']))
      file.write("   }\n")
   if visual:
      print("}")
   file.write("}")

file.close()

print("Configuration file %s/luns_%s.conf created"%(dir,ip.split('.')[-1]))

if restart:
   os.system("systemctl restart multipathd")
   print("multipathd restarted")
