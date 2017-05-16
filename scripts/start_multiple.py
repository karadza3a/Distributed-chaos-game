import os
import subprocess
from threading import Thread
from time import sleep
import tkinter as tk

import pexpect as pexpect


class Interface(tk.Frame):
    def __init__(self, start_port, num_instances, master=None):
        tk.Frame.__init__(self, master)
        self.bootstrap_started = False
        self.cpanel_started = False
        self.pack()
        self.start_port = start_port
        self.num_instances = num_instances
        self.cpanel = None
        self.bootstrap = None
        self.servents = {}
        # widgets
        self.port_input = tk.Entry(self)
        self.port_input.pack(side="left")
        self.msg_input = tk.Entry(self)
        self.msg_input.pack(side="right")
        self.send_button = tk.Button(self, text="Send", fg="red", command=self.send_command)
        self.send_button.pack(side="bottom")
        self.quit_button = tk.Button(self, text="QUIT", fg="red", command=self.quit)
        self.quit_button.pack(side="top")
        self.start_all()

    def send_command(self):
        port = self.port_input.get()
        if port in self.servents:
            s = self.servents[port]  # type: pexpect.spawn
            s.send(self.msg_input.get() + "\n")
            print(s.expect(["started job .*!", "showing...", "unknown id"]))
        else:
            print("Servent not found")

    def quit(self):
        for s in self.servents.values():  # type: pexpect.spawn
            s.sendline("q")
            s.expect("Quitting...")
            s.expect("bye")
        self.bootstrap.sendline("q")
        self.bootstrap.expect("Quitting...")
        self.bootstrap.expect("bye")
        self.cpanel.sendline("q")
        self.master.destroy()

    def start_bootstrap(self):
        f = os.path.abspath('out/b_out.txt')
        cmd = " ".join(["/usr/local/Cellar/python3/3.6.1/bin/python3",
                        "/Users/andrejk/PycharmProjects/kidsp/bootstrap/__init__.py -l", f])
        self.bootstrap = pexpect.spawn(cmd)
        self.bootstrap.expect("Bootstrap listening on port (\d+)...")
        self.bootstrap.expect("q to quit:")
        self.bootstrap_started = True

    def start_cpanel(self):
        f = os.path.abspath('out/c_out.txt')
        cmd = " ".join(["/usr/local/Cellar/python3/3.6.1/bin/python3",
                        "/Users/andrejk/PycharmProjects/kidsp/cpanel/__init__.py -l", f])
        self.cpanel = pexpect.spawn(cmd)
        self.cpanel.expect("CPanel listening on port (\d+)...")
        self.cpanel.expect("q to quit:")
        self.cpanel_started = True

    def start_servent(self, port):
        f = os.path.abspath('out/out_%s.txt' % port)
        cmd = " ".join(["/usr/local/Cellar/python3/3.6.1/bin/python3",
                        "/Users/andrejk/PycharmProjects/kidsp/servent/main.py", "-p", port, "-l", f])
        self.servents[port] = pexpect.spawn(cmd)
        self.servents[port].expect("q to quit:")

    def start_all(self, ):
        tc = Thread(target=self.start_cpanel)
        tc.start()
        while not self.cpanel_started:
            pass
        tb = Thread(target=self.start_bootstrap)
        tb.start()
        while not self.bootstrap_started:
            pass

        for port in range(self.start_port, self.start_port + self.num_instances):
            ts = Thread(target=self.start_servent, args=(str(port),))
            ts.start()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(dest="start_port", type=int)
    parser.add_argument(dest="num_instances", type=int)
    args = parser.parse_args()

    root = tk.Tk()
    app = Interface(args.start_port, args.num_instances, master=root)
    app.mainloop()
