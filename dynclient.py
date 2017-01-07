#!/usr/bin/python2
"""
DynDNS updater daemon, Copyright (c) 2011, Keivan Motavalli
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

  1) Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
  2) Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import os, sys, getopt, httplib, time, base64, ConfigParser, datetime, re
def main(argv):
	confPath = "/etc/dynclient.conf"
	helpmessage = "usage: dynclient.py -c <config file> --config=<config file>\n-h --help: prints this message\n-e --exampleconfiguration: prints a configuration example\n-k <config file> --killchilds=<config file>"
	configExample = "[general]\nusername = myuser\npassword = mypassword\ndomains = example1.dyndns.org,example2.onlyforfun.net,example3.dynalias.net\nlogfile = /var/log/dynclient.log\nfrequency = 60\n"
	confinst = configuration()
	daemonwork = daemonWork()
	try:
		opts, args = getopt.getopt(argv,"c:hek:",["config=","help","exampleconfiguration","killchilds="])
	except getopt.GetoptError:
		print helpmessage
		sys.exit(2)	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print helpmessage
			sys.exit(0)
		elif opt in ("-e", "--exampleconfiguration"):
			print configExample
			sys.exit(0)
		elif opt in ("-c", "--config"):
			confPath = arg
		elif opt in ("-k", "--killchilds"):
			print "killing all the daemons currently running with the same configuration"
			if confinst.parseConf(arg) == 0:
				if daemonwork.killChilds(confinst.returnValue("logfile"), 1) == 0:
					print "success, exiting"
					sys.exit(0)
				else:
					print "ouch! something failed. exiting"
					sys.exit(1)
			else:
				sys.exit(2)
	if confinst.parseConf(confPath) == 0:
		print "Success! daemon starting"
	else:
		sys.exit(1)
	daemonwork.killChilds(confinst.returnValue("logfile"), 0)
	confinst.createAuthString()
	daemonwork.forkDaemon()
	daemonwork.runDaemon()
	
def tolog(string):
	confinst = configuration()
	try:
		log = open(confinst.returnValue("logfile"), "a")
		now = datetime.datetime.now()
		string = str(now.year) + "/" + str(now.month) + "/" + str(now.day) + " at " + str(now.hour) + ":" + str(now.minute) + ":" + str(now.second) + ":" + str(now.microsecond) + ": " + string + "\n"
		log.write(string)
		log.close
	except:
		print "I still can't log errors at this stage!"

class configuration:
	Params = {'frequency': 60}
	authStringB64 = None
	def parseConf(self, confPath):
		if confPath != None:
			config = ConfigParser.ConfigParser()
			if os.path.isfile(confPath) == True:
				try:
					config.read(confPath)
					for value in ["logfile", "username", "password", "frequency", "domains"]:
						try:
							configuration.Params[value] = config.get('general', value)
						except: 
							print "error parsing config value " + value
							tolog("error parsing config value " + value)
							return 1
				except:
					print "General error parsing config"
					tolog("General error parsing config")
					return 1
			else:
				print "error reading config; you have to create it first at /etc/dynclient.conf or at a path specified with -c/--config=; example config below; remember to create the log file too\n"
				print "[general]\nusername = myuser\npassword = mypassword\ndomains = example1.dyndns.org,example2.onlyforfun.net,example3.dynalias.net\nlogfile = /var/log/dynclient.log\nfrequency = 60\n"
				return 1
			if os.path.isfile(self.returnValue("logfile")) == False:
				print "you have to create a logfile for me at " + self.returnValue("logfile")
				return 1
			if os.access(self.returnValue("logfile"), os.W_OK) == True:
				tolog("configuration parsed")
				return 0
			else:
				print "you have to make the logfile (" + self.returnValue("logfile") + ") writable by the user dynclient.py runs under"
				return 1
		else:
			print "parseConf here, you didn't pass me a path!"
			tolog("parseConf here, you didn't pass me a path!") #Am I really able to log at this stage?
			return 1
	def returnValue(self, requestedValue = None):
		if requestedValue != None:
			if requestedValue in ("logfile", "username", "password", "frequency", "domains"):
				return configuration.Params[requestedValue]
			else:
				tolog("returnValue here, the value you requested is invalid")
				return 1
		else: 
			tolog("returnValue here, you didn't passs me a value to return!")
			return 1
	def createAuthString(self):
		configuration.authStringB64 = "Basic " + base64.encodestring(self.returnValue("username") + ":" + self.returnValue("password"))
		

class daemonWork:
	confinst = configuration()
	def forkDaemon(self):
		global child_pid
		child_pid = os.fork()
		if child_pid == 0:
			print "Child Process: PID# %s" % os.getpid()
			tolog("daemon pid: %s" %os.getpid())
		else:
			print "Parent Process: PID# %s" % os.getpid()
			exit(0)
	def getip(self):
		try:
			ipregex = re.compile('[0-9]+(?:\.[0-9]+){3}')
			getipconn = httplib.HTTPConnection("checkip.dyndns.org", timeout=10)
			getipconn.request("GET", "/")
			response = getipconn.getresponse()
			currentip = ipregex.findall(response.read())[0]
			if response.status != 200:
				tolog("can't get current ip for reason : " + str(response.status) + " " + response.reason + "exit")
				return error
			else:
				return currentip
		except:
			tolog("error reading from checkip.dyndns.org")
			return "error"
	def updatedyn(self, ip):
		for currentDomain in daemonWork.confinst.returnValue("domains").split(","):
			try:
				url = '/nic/update?hostname=' + currentDomain + '&myip=' + ip
				updateipconn = httplib.HTTPSConnection("members.dyndns.org", timeout=20) #NO certificate validation! An active attacker could easily perform a MITM attack. 
				updateipconn.putrequest("GET", url)
				updateipconn.putheader("host", "members.dyndns.org")
				updateipconn.putheader("User-Agent", "dynclient.py")
				updateipconn.putheader("Authorization", daemonWork.confinst.authStringB64)
				updateipconn.putheader("Content-type", "application/x-www-form-urlencoded")
				updateipconn.endheaders()
				response = updateipconn.getresponse().read()
				tolog(currentDomain + " : " + response)
				return 0
			except:
				tolog("error updating ip; the connection may have been reset by the other peer.")
				return 1

	def runDaemon(self):
		oldip = "0"
		failed = 0
		while 1:
			currentip = self.getip()
			if failed == 0:
				if currentip != "error":
					if currentip != oldip:
						failed = self.updatedyn(currentip)
				else:
					tolog("error comparing ip addresses; maybe conn timeout?")
			else:
				if currentip != "error":
					failed = self.updatedyn(currentip)
				else:
					tolog("TFU")
			if currentip != "error":
				oldip = currentip
			time.sleep(int(daemonWork.confinst.returnValue("frequency")))
	def killChilds(self, logfile, output):
		try:
			with open(logfile, 'r') as infile:
				for line in infile:
					if "daemon pid:" in line:
						pid = line.split("\n")[0].split(" ")[5]
						try:
							os.kill(int(pid), 15)
							if output == 1:
								print "process " + pid + " terminated"
						except:
							if output == 1:
								print "process " + pid + " was already terminated"
			tolog("killing my childs")
			return 0
		except:
			return 1
if __name__ == "__main__":
	main(sys.argv[1:])
