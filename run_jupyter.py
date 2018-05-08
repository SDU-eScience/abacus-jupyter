#!/usr/bin/env python

# Import needed modules
import os
import sys
import webbrowser
from subprocess import Popen, PIPE

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

# Define JupyterTool class
class JupyterTool:
	uid = None
	username = None
	status = None
	tunnel = None
	hostname = "fe.deic.sdu.dk"
	port = None
	token = None
	jpt_jobid = None
	jpt_status = None
	jpt_node = None

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
		value = self.get_value(config, "version", "Python 3.6")
		self.string_version.set(value)

	def add_log(self, text):
		self.text_info.configure(state = tk.NORMAL)
		self.text_info.insert(tk.END, text + "\n")
		self.text_info.configure(state = tk.DISABLED)
		self.text_info.see(tk.END)
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
		if keyfile == "":
			proc = Popen(["ssh", "-q", address, cmd], stdout=PIPE)
		else:
			proc = Popen(["ssh", "-q", "-i", keyfile, address, cmd], stdout=PIPE)
		out, err = proc.communicate()
		out = out.decode().strip()
		return out, proc.returncode

	def get_uid(self):
		out, exitcode = self.ssh_command("echo $UID")
		if exitcode:
			return 0
		else:
			return int(out)

	def open_tunnel(self):
		self.port = str(10000 + self.uid)
		address = self.username + "@" + self.hostname
		keyfile = self.entry_sshkey.get().strip()
		cmd = "ssh -q -N -L " + self.port + ":localhost:" + self.port + " " + self.jpt_node
		if keyfile == "":
			self.tunnel = Popen(["ssh", "-q", "-L", "8888:localhost:" + self.port, address, cmd])
		else:
			self.tunnel = Popen(["ssh", "-q", "-i", keyfile, "-L", "8888:localhost:" + self.port, address, cmd])
		self.status = 1

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
		self.status = None

	def wait_tunnel(self):
		self.poll_jupyter()
		if self.jpt_status == "R":
			self.add_log("Jupyter is currently running")
			self.open_tunnel()
			if self.poll_tunnel():
				self.add_log("Established SSH tunnel using port " + self.port)
				self.button_connect.configure(text = "Disconnect", command = self.disconnect)
				self.button_open.configure(state = tk.NORMAL)
			else:
				self.add_log("Failed to establish SSH tunnel using port " + self.port)
			return
		elif self.jpt_status == "PD":
			self.add_log("Jupyter is currently pending, please wait")
		else:
			self.add_log("Jupyter status is currently unknown")
		self.root.after(5000, self.wait_tunnel)

	def connect(self):
		self.username = self.entry_username.get()
		self.uid = self.get_uid()
		if self.uid == 0:
			self.add_log("Unable to connect as: " + self.username)
			return
		else:
			self.add_log("Successfully connected as: " + self.username + " (" + str(self.uid) + ")")
		if self.poll_jupyter():
			self.add_log("Jupyter instance found with jobid " + self.jpt_jobid)
			self.wait_tunnel()
		else:
			self.add_log("Jupyter instance was not found")
			if self.start_jupyter():
				self.wait_tunnel()

	def disconnect(self):
		self.stop_jupyter()
		if self.poll_tunnel():
			self.close_tunnel()
			self.add_log("Closed SSH tunnel")
		else:
			self.add_log("No active SSH tunnel found")
		self.button_connect.configure(text = "Connect", command = self.connect)
		self.button_open.configure(state = tk.DISABLED)

	def start_jupyter(self):
		version = "3"
		account = self.entry_account.get()
		if "2.7" in self.string_version.get():
			version = "2"
		if not self.validate_time():
			return 0
		tmlimit = self.entry_time.get()
		cmd = "/home/hansen/source/jupyter/jpt_start " + version + " " + account + " " + tmlimit
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
			return 0

	def stop_jupyter(self):
		if self.poll_jupyter():
			self.add_log("Stopping Jupyter with jobid " + self.jpt_jobid)
			cmd = "scancel -u " + self.username + " -n jupyter"
			self.ssh_command(cmd)
		else:
			self.add_log("No instance of Jupyter is running")

	def open_jupyter(self):
		if not self.token:
			cmd = "cat ~/.jupyter/token"
			out, exitcode = self.ssh_command(cmd)
			self.token = out
		url = "http://localhost:8888/?token=" + self.token
		webbrowser.open_new_tab(url)

	def close_window(self):
		if self.status:
			self.close_tunnel()
			self.stop_jupyter()
		self.save_settings()
		self.root.destroy()

	def open_sshkey(self):
		self.root.update()
		filename = filedialog.askopenfilename(initialdir = "/", title = "Select private SSH key")
		self.entry_sshkey.delete(0, tk.END)
		self.entry_sshkey.insert(0, filename)

	def __init__(self, root):
		self.root = root
		self.root.title("Jupyter on ABACUS 2.0")
		self.root.protocol("WM_DELETE_WINDOW", self.close_window)
		self.frame = tk.Frame(self.root, width = 710, height = 480)
		self.frame.pack()

		self.label_settings = tk.Label(self.frame, text = "Settings", font = (None, 24))
		self.label_settings.place(x = 40, y = 30, anchor = tk.W)

		self.label_username = tk.Label(self.frame, text = "Username")
		self.label_username.place(x = 40, y = 60, anchor = tk.W)
		self.entry_username = tk.Entry(self.frame)
		self.entry_username.place(x = 40, y = 82, anchor = tk.W, width = 250)

		self.label_sshkey = tk.Label(self.frame, text = "SSH key (optional)")
		self.label_sshkey.place(x = 300, y = 60, anchor = tk.W)
		self.entry_sshkey = tk.Entry(self.frame)
		self.entry_sshkey.place(x = 300, y = 82, anchor = tk.W, width = 315)
		self.button_sshkey = tk.Button(self.frame, text = "...", command = self.open_sshkey)
		self.button_sshkey.place(x = 618, y = 82, anchor = tk.W)

		self.label_account = tk.Label(self.frame, text = "Account")
		self.label_account.place(x = 40, y = 120, anchor = tk.W)
		self.entry_account = tk.Entry(self.frame)
		self.entry_account.place(x = 40, y = 142, anchor = tk.W, width = 200)

		self.label_time = tk.Label(self.frame, text = "Time limit (hh:mm)")
		self.label_time.place(x = 250, y = 120, anchor = tk.W)
		self.entry_time = tk.Entry(self.frame)
		self.entry_time.place(x = 250, y = 142, anchor = tk.W, width = 200)

		self.label_version = tk.Label(self.frame, text = "Version")
		self.label_version.place(x = 460, y = 120, anchor = tk.W)
		self.string_version = tk.StringVar(self.frame)
		self.select_version = tk.OptionMenu(self.frame, self.string_version, "Python 3.6", "Python 2.7")
		self.select_version.place(x = 460, y = 142, anchor = tk.W, width = 200)

		self.button_connect = tk.Button(self.frame, text = "Connect", command = self.connect)
		self.button_connect.place(x = 40, y = 180, anchor = tk.W)

		self.label_info = tk.Label(self.frame, text = "Information", font = (None, 24))
		self.label_info.place(x = 40, y = 235, anchor = tk.W)
		self.text_info = tk.Text(self.frame, height = 10, width = 87, relief = tk.RIDGE, bd = 2, state = tk.DISABLED)
		self.text_info.place(x = 40, y = 335, anchor = tk.W)

		self.button_open = tk.Button(self.frame, text = "Open Jupyter in browser", command = self.open_jupyter, state = tk.DISABLED)
		self.button_open.place(x = 40, y = 440, anchor = tk.W)

		self.load_settings();

# Create and launch the application
root = tk.Tk()
JupyterTool(root)
root.mainloop()
