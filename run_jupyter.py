#!/usr/bin/env python

# Import needed modules
import os
import sys
import webbrowser
import subprocess
import platform

try:
	import Tkinter as tk
except ImportError:
	pass

try:
	import tkinter as tk
except ImportError:
	pass

try:
	tk
except NameError:
	pass
	print("Please install the python TK package to use this program")
	sys.exit()

try:
	import tkFileDialog as filedialog
except ImportError:
	from tkinter import filedialog

try:
	from ConfigParser import SafeConfigParser as ConfigParser
except ImportError:
	from configparser import ConfigParser

try:
	import urllib.request as url
except ImportError:
	import urllib as url

# Define UpdateWindow class
class UpdateWindow:
	def close_window(self):
		self.root.destroy()

	def __init__(self, parent):
		self.root = tk.Toplevel(parent)
		self.parent = parent

		self.root.title("Update required")
		self.root.geometry("+%d+%d" % (parent.winfo_rootx()+100, parent.winfo_rooty()+100))
		self.root.grab_set()
		self.root.transient(parent)
		self.root.lift()

		self.label_info = tk.Label(self.root, text = "A new version of the program is available.\nPlease click the button below to update the program.\nAfter the program exits, please restart it manually.")
		self.label_info.pack(padx = 10, pady = 10)

		self.button_update = tk.Button(self.root, text = "Update", width = 6, command = self.close_window)
		self.button_update.pack(pady = (0,15))

		self.root.protocol("WM_DELETE_WINDOW", self.close_window)
		parent.wait_window(self.root)

# Define MainWindow class
class MainWindow:
	hostname = "fe.deic.sdu.dk"
	jpt_root = "/opt/sys/apps/jpt/"
	jpt_version = 1.2
	uid = None
	username = None
	status = None
	tunnel = None
	port = None
	token = None
	jpt_jobid = None
	jpt_status = None
	jpt_node = None

	def check_ssh_exists(self):
		if os.name == 'nt':
			exitcode = subprocess.call(["where", "plink"], stdout = subprocess.PIPE)
			client = "PuTTY"
		else:
			exitcode = subprocess.call(["which", "ssh"], stdout = subprocess.PIPE)
			client = "OpenSSH"
		if exitcode:
			self.add_log("Unable to find a valid SSH client, please install " + client)
			self.disable_connect()

	def update_program(self):
		filename = os.path.realpath(__file__)
		cmd = "cat " + self.jpt_root + "run_jupyter.py"
		out, exitcode = self.ssh_command(cmd)
		fp = open(filename, "w")
		fp.write(out)
		fp.close()
		self.root.destroy()
		sys.exit()

	def check_version(self):
		cmd = "cat " + self.jpt_root + "jpt_version"
		out, exitcode = self.ssh_command(cmd)
		out = float(out)
		if out > self.jpt_version:
			UpdateWindow(self.root)
			self.update_program()

	def save_settings(self):
		config = ConfigParser()
		config.add_section("main")
		value = self.entry_username.get()
		config.set("main", "username", value)
		value = self.entry_sshkey.get()
		config.set("main", "sshkey", value)
		value = self.entry_account.get()
		config.set("main", "account", value)
		value = self.entry_time.get()
		config.set("main", "timelimit", value)
		value = self.string_version.get()
		config.set("main", "version", value)
		with open(os.path.expanduser("~/.jupytertool"), "w") as f:
			config.write(f)

	def get_value(self, config, key, default):
		try:
			value = config.get("main", key)
		except:
			value = default
		return value

	def load_settings(self):
		config = ConfigParser()
		config.read(os.path.expanduser("~/.jupytertool"))
		value = self.get_value(config, "username", "")
		self.entry_username.insert(0, value)
		value = self.get_value(config, "sshkey", "")
		self.entry_sshkey.insert(0, value)
		value = self.get_value(config, "account", "default")
		self.entry_account.insert(0, value)
		value = self.get_value(config, "timelimit", "06:00")
		self.entry_time.insert(0, value)
		value = self.get_value(config, "version", "")
		if not value in self.array_version:
			value = self.array_version[0]
		self.string_version.set(value)

	def add_log(self, text):
		self.text_info.configure(state = tk.NORMAL)
		self.text_info.insert(tk.END, text + "\n")
		self.text_info.configure(state = tk.DISABLED)
		self.text_info.see(tk.END)
		self.root.update()

	def disable_connect(self):
		self.button_connect.configure(state = tk.DISABLED)
		self.root.update()

	def set_connect(self):
		self.button_connect.configure(text = "Connect", command = self.connect)
		self.button_connect.configure(state = tk.NORMAL)
		self.root.update()

	def set_disconnect(self):
		self.button_connect.configure(text = "Disconnect", command = self.disconnect)
		self.button_connect.configure(state = tk.NORMAL)
		self.root.update()

	def validate_time(self):
		tm = self.entry_time.get()
		tm = tm.split(":")
		if not len(tm) == 2:
			self.add_log("Invalid format for time limit")
			return 0
		if not tm[0].isdigit():
			self.add_log("Invalid format for time limit")
			return 0
		if not tm[1].isdigit():
			self.add_log("Invalid format for time limit")
			return 0
		hh = int(tm[0])
		mm = int(tm[1])
		tot = 60*hh + mm
		if tot > 24*60:
			self.add_log("Time limit exceeds the maximal value of 24 hours")
			return 0
		return 1

	def ssh_command(self, cmd):
		address = self.username + "@" + self.hostname
		keyfile = self.entry_sshkey.get().strip()
		if os.name == 'nt':
			cmdline = ["plink"]
			flag = True
		else:
			cmdline = ["ssh", "-q"]
			flag = False
		if not keyfile:
			cmdline.extend([address, cmd])
		else:
			cmdline.extend(["-i", keyfile, address, cmd])
		proc = subprocess.Popen(cmdline, stdout = subprocess.PIPE, stdin = subprocess.PIPE, shell = flag)
		out, err = proc.communicate(b"y\n")
		out = out.decode().strip()
		return out, proc.returncode

	def get_uid(self):
		out, exitcode = self.ssh_command("echo $UID")
		if exitcode:
			return 0
		else:
			return int(out)

	def poll_webserver(self):
		try:
			result = url.urlopen("http://localhost:8448").getcode()
		except:
			return 0
		if result == 200:
			return 1
		else:
			return 0

	def wait_webserver(self):
		if not self.poll_tunnel():
			return
		if self.poll_webserver():
			self.add_log("Jupyter webserver is up and running")
			self.button_open.configure(state = tk.NORMAL)
			self.root.update()
		else:
			if not self.poll_jupyter():
				self.add_log("Jupyter job unexpectedly stopped")
				self.disconnect()
				return
			else:
				self.add_log("Jupyter webserver is not responding, please wait")
				self.root.after(5000, self.wait_webserver)

	def open_tunnel(self):
		self.port = str(10000 + self.uid)
		address = self.username + "@" + self.hostname
		forward = "8448:" + self.jpt_node + ":" + self.port
		keyfile = self.entry_sshkey.get().strip()
		if os.name == 'nt':
			cmdline = ["plink"]
			flag = True
		else:
			cmdline = ["ssh", "-q"]
			flag = False
		if not keyfile:
			cmdline.extend(["-N", "-L", forward, address])
		else:
			cmdline.extend(["-i", keyfile, "-N", "-L", forward, address])
		self.tunnel = subprocess.Popen(cmdline, shell = flag)
		self.status = True

	def poll_tunnel(self):
		if self.status == None:
			return 0
		if self.tunnel.poll() == None:
			return 1
		else:
			return 0

	def close_tunnel(self):
		if self.poll_tunnel():
			self.tunnel.terminate()
			self.add_log("Closed SSH tunnel")
		self.status = None

	def wait_tunnel(self):
		if not self.poll_jupyter():
			return
		else:
			self.set_disconnect()
		if self.jpt_status == "R":
			self.add_log("Jupyter is currently running")
			self.open_tunnel()
			if self.poll_tunnel():
				self.add_log("Established SSH tunnel using port " + self.port)
				self.wait_webserver()
			else:
				self.add_log("Failed to establish SSH tunnel using port " + self.port)
				self.set_connect()
			return
		elif self.jpt_status == "PD":
			self.add_log("Jupyter is currently pending, please wait")
		else:
			self.add_log("Jupyter status is currently unknown")
		self.root.after(5000, self.wait_tunnel)

	def connect(self):
		self.disable_connect()
		self.username = self.entry_username.get().strip()
		if not self.username:
			self.add_log("Unable to connect without a username")
			self.set_connect()
			return
		self.uid = self.get_uid()
		if self.uid == 0:
			self.add_log("Unable to connect as: " + self.username)
			self.set_connect()
			return
		else:
			self.add_log("Successfully connected as: " + self.username + " (" + str(self.uid) + ")")
			self.check_version()
		if self.poll_jupyter():
			self.add_log("Jupyter instance found with jobid " + self.jpt_jobid)
		else:
			self.add_log("Jupyter instance was not found")
			if not self.start_jupyter():
				self.set_connect()
				return
		self.set_connect()
		self.wait_tunnel()

	def disconnect(self):
		self.stop_jupyter()
		self.close_tunnel()
		self.button_open.configure(state = tk.DISABLED)
		self.set_connect()

	def start_jupyter(self):
		version = "3"
		jupyter = "nb"
		account = self.entry_account.get()
		if "2.7" in self.string_version.get():
			version = "2"
		if "Lab" in self.string_version.get():
			jupyter = "lab"
		if not self.validate_time():
			return 0
		tmlimit = self.entry_time.get()
		cmd = self.jpt_root + " ".join(["jpt_start", version, jupyter, account, tmlimit])
		out, exitcode = self.ssh_command(cmd)
		if "invalid" in out:
			self.add_log("Cannot start Jupyter, invalid account: " + account)
			return 0
		else:
			out = out.split(" ")
			self.add_log("Started new Jupyter instance with jobid " + out[1])
			return 1

	def poll_jupyter(self):
		cmd = "squeue -h -u " + self.username + " -n jupyter | awk '{ print $1, $5, $8 }'"
		out, exitcode = self.ssh_command(cmd)
		if out:
			out = out.split(" ")
			self.jpt_jobid = out[0]
			self.jpt_status = out[1]
			self.jpt_node = out[2]
			return 1
		else:
			self.jpt_jobid = None
			self.jpt_status = None
			self.jpt_node = None
			return 0

	def stop_jupyter(self):
		if self.poll_jupyter():
			self.add_log("Stopping Jupyter with jobid " + self.jpt_jobid)
			cmd = "scancel -u " + self.username + " -n jupyter"
			self.ssh_command(cmd)
		self.jpt_jobid = None
		self.jpt_status = None
		self.jpt_node = None

	def open_jupyter(self):
		if not self.token:
			cmd = "cat ~/.jupyter/token"
			out, exitcode = self.ssh_command(cmd)
			self.token = out
		url = "http://localhost:8448/?token=" + self.token
		self.add_log("URL address: " + url)
		webbrowser.open_new_tab(url)

	def close_window(self):
		if self.jpt_jobid:
			self.stop_jupyter()
		if self.status:
			self.close_tunnel()
		self.save_settings()
		self.root.destroy()

	def open_sshkey(self):
		self.root.update()
		filename = filedialog.askopenfilename(initialdir = os.path.expanduser("~"), title = "Select private SSH key")
		self.entry_sshkey.delete(0, tk.END)
		self.entry_sshkey.insert(0, filename)

	def __init__(self, root):
		self.root = root
		self.root.title("Jupyter on ABACUS 2.0")
		self.root.protocol("WM_DELETE_WINDOW", self.close_window)
		self.frame = tk.Frame(self.root)
		self.frame.pack(padx = 40, pady = 20)

		self.label_settings = tk.Label(self.frame, text = "Settings", font = (None, 24))
		self.label_settings.grid(row = 0, column = 0, sticky = tk.W)

		self.aframe = tk.Frame(self.frame)
		self.aframe.grid(row = 1, column = 0, sticky = tk.W)
		self.bframe = tk.Frame(self.frame)
		self.bframe.grid(row = 2, column = 0, pady = 5, sticky = tk.W)

		self.label_username = tk.Label(self.aframe, text = "Username")
		self.label_username.grid(row = 0, column = 0, sticky = tk.W)
		self.entry_username = tk.Entry(self.aframe, width = 20)
		self.entry_username.grid(row = 1, column = 0, sticky = tk.W)

		self.label_sshkey = tk.Label(self.aframe, text = "SSH key (optional)")
		self.label_sshkey.grid(row = 0, column = 1, padx = 5, sticky = tk.W)
		self.entry_sshkey = tk.Entry(self.aframe, width = 37)
		self.entry_sshkey.grid(row = 1, column = 1, padx = 5, sticky = tk.W)
		self.button_sshkey = tk.Button(self.aframe, text = "...", command = self.open_sshkey)
		self.button_sshkey.grid(row = 1, column = 2, sticky = tk.W)

		self.label_account = tk.Label(self.bframe, text = "Account")
		self.label_account.grid(row = 0, column = 0, sticky = tk.W)
		self.entry_account = tk.Entry(self.bframe, width = 20)
		self.entry_account.grid(row = 1, column = 0, sticky = tk.W)

		self.label_time = tk.Label(self.bframe, text = "Time limit (hh:mm)")
		self.label_time.grid(row = 0, column = 1, padx = 5, sticky = tk.W)
		self.entry_time = tk.Entry(self.bframe, width = 20)
		self.entry_time.grid(row = 1, column = 1, padx = 5, sticky = tk.W)

		self.label_version = tk.Label(self.bframe, text = "Version")
		self.label_version.grid(row = 0, column = 2, sticky = tk.W)
		self.array_version = ["Python 3.6 (Jupyter Notebook)", "Python 3.6 (JupyterLab)", "Python 2.7 (Jupyter Notebook)", "Python 2.7 (JupyterLab)"]
		self.string_version = tk.StringVar(self.bframe)
		self.select_version = tk.OptionMenu(self.bframe, self.string_version, *self.array_version)
		self.select_version.configure(width = 20)
		self.select_version.grid(row = 1, column = 2, sticky = tk.W)

		self.button_connect = tk.Button(self.frame, text = "Connect", width = 10, command = self.connect)
		self.button_connect.grid(row = 3, column = 0, pady = 5, sticky = tk.W)

		self.label_info = tk.Label(self.frame, text = "Information", font = (None, 24))
		self.label_info.grid(row = 4, column = 0, pady = (15,4), sticky = tk.W)

		self.text_info = tk.Text(self.frame, height = 10, relief = tk.RIDGE, bd = 2)
		self.text_info.configure(highlightthickness = 0, state = tk.DISABLED)
		self.text_info.bind("<1>", lambda event: self.text_info.focus_set())
		self.text_info.grid(row = 5, column = 0, sticky = tk.W + tk.E)

		self.button_open = tk.Button(self.frame, text = "Open Jupyter in browser", command = self.open_jupyter, state = tk.DISABLED)
		self.button_open.grid(row = 6, column = 0, pady = (15,10), sticky = tk.W)

		if platform.system() == 'Windows':
			self.select_version.configure(width = 30)
			self.entry_sshkey.configure(width = 54)
			self.text_info.configure(width = 60)

		if platform.system() == 'Linux':
			self.select_version.configure(width = 25)
			self.entry_sshkey.configure(width = 46)

		self.load_settings()
		self.check_ssh_exists()

# Create and launch the application
root = tk.Tk()
MainWindow(root)
root.mainloop()
