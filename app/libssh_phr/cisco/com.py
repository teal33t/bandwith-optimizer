#!/usr/bin/env python

import paramiko
import time 
import sys
import re

class ssh:	
	
	priv = False
	
	def __init__(self, host, username, password, enpassword):
		(ip, port) = host.split(':')
		
		self.enpassword = enpassword
		self.ssh = paramiko.SSHClient()
		self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		try:
			self.ssh.connect(ip, int(port), username=username, password=password)
		except Exception as exception:
			print(exception)
		else:
			try:
				self.conn = self.ssh.invoke_shell()
			except Exception as exception:
				print(exception)
				exit()
			else:
				print('* Connected successfully to %s' % (ip))
				self._disable_paging()
				self._get_hostname()
				if not self._enable():
					print('Error: Can not get privilaged mode. Device returns "ACCESS DENIED"')
				else:
					self.priv = True
					print('* Got privilaged mode on %s' % (ip))

	def close(self):
		self.ssh.close()	
	
	def _recv(self):
		if self.conn.recv_ready():
			return self.conn.recv(9999)
		else:
			return False
	
	def _clear(self):
		time.sleep(0.1)
		self._recv()

	def _disable_paging(self):
		self.conn.send('terminal length 0\n')

	def _enable(self):
		self.conn.send('enable\n')
		self.conn.send(self.enpassword + "\n")
		time.sleep(0.1)
		output = self._recv()
		p = re.compile('Access denied', re.M)
		if p.search(output):
			return False
		else:
			return True
		
	def _get_hostname(self):
		self._clear()
		self.conn.send("\n")
		time.sleep(0.01)
		output = self._recv()
		self.hostname = output.strip()[0:-1]
    
	def send(self, cmd, timeo=60):
		timeo = 60 if timeo == 0 else timeo  
		interval = 0.01
		p = re.compile('^'+self.hostname+'.*#', re.M)
		self.conn.send("%s\n" % cmd)

		output = ''
		c = 0
		while(True):
			c += 1
			if c * interval >= timeo:
				print('Error: Command time out of %s seconds reached' % timeo)
				break
			time.sleep(interval)
			chunk = self._recv()
			if chunk:
				output += chunk
			if p.search(output):
				break
		return '>' + output[:output.rfind('\n')]
	
	def batch_send(self, cmd, timeo=0):
		commands = cmd.splitlines()
		output = ''
		for command in commands:
			output += self.send(command, timeo) + '\n'
		return output
	
	def file_send(self, filename, timeo=0):
		try:
			f = open(filename)
		except Exception as exception:
			print(exception)
			exit()
		else:
			content = f.read()
			return self.batch_send(content)
		return False
