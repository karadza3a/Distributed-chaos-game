import os
import traceback

from appJar import gui
from threading import Thread
import pexpect as pexpect
import common.communication as comm

START_PORT = 9000


class Interface:
    def __init__(self, the_app):
        self.app = the_app  # type: gui
        self.bootstrap_started = False
        self.cpanel_started = False
        self.cpanel = None
        self.bootstrap = None
        self.servents = {}
        self.next_port = START_PORT

    def send_servent_command(self, port, msg):
        if port in self.servents:
            s = self.servents[port]  # type: pexpect.spawn
            s.send(msg + "\n")
            s.expect(["started job .*!", "showing...", "unknown id"])
            output = self.app.getTextArea("output") + "\n" + str(s.match.string)
            self.app.setTextArea("output", output)
        else:
            print("Servent not found")

    def send_cpanel_command(self, msg):
        if self.cpanel_started:
            comm.Communicator.cpanel_input_command(msg)
        else:
            print("Cpanel not started")

    def quit(self):
        for s in self.servents.values():  # type: pexpect.spawn
            try:
                s.sendline("q")
                s.expect("Quitting...")
                s.expect("bye")
            except OSError:
                traceback.print_exc()

        try:
            if self.bootstrap_started:
                self.bootstrap.sendline("q")
                self.bootstrap.expect("Quitting...")
        except OSError:
            traceback.print_exc()
        try:
            if self.cpanel_started:
                self.bootstrap.expect("bye")
                self.cpanel.sendline("q")
        except OSError:
            traceback.print_exc()

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

    def check_cpanel(self):
        if comm.ENABLE_CPANEL and not self.cpanel_started:
            tc = Thread(target=self.start_cpanel)
            tc.start()
            while not self.cpanel_started:
                pass

    def user_start_bootstrap(self, _):
        self.check_cpanel()

        tb = Thread(target=self.start_bootstrap)
        tb.start()
        while not self.bootstrap_started:
            pass

    def user_start_servents(self, _):
        self.check_cpanel()
        num_instances = int(self.app.getEntry("Num servents"))
        for port in range(self.next_port, self.next_port + num_instances):
            ts = Thread(target=self.start_servent, args=(str(port),))
            ts.start()

        self.next_port += num_instances

    def user_quit(self):
        self.quit()
        return True

    def user_job_start(self, _):
        port = str(int(self.app.getEntry("port")))
        n = int(self.app.getEntry("n"))
        r = float(self.app.getEntry("r"))
        w = int(self.app.getEntry("w"))
        h = int(self.app.getEntry("h"))
        msg = "start %d %f %d %d" % (n, r, w, h)
        self.send_servent_command(port, msg)

    def user_job_stop(self, _):
        port = str(int(self.app.getEntry("port")))
        self.send_servent_command(port, "stop " + self.app.getEntry("job_id"))

    def user_job_show(self, _):
        port = str(int(self.app.getEntry("port")))
        self.send_servent_command(port, "show " + self.app.getEntry("job_id"))

    def user_settings_changed(self, _):
        if self.cpanel_started or self.bootstrap_started:
            # TODO warn that nothing's gonna happen
            pass

        comm.BOOTSTRAP_HOST = self.app.getEntry("BS host")
        comm.BOOTSTRAP_PORT = int(self.app.getEntry("BS port"))
        comm.CPANEL_HOST = self.app.getEntry("CP host")
        comm.CPANEL_PORT = int(self.app.getEntry("CP port"))
        comm.SERVENT_HOST = self.app.getEntry("Servent host")
        comm.ENABLE_CPANEL = self.app.getCheckBox("CPanel")
        self.next_port = int(self.app.getEntry("Servent start port"))

        with open("../common/config.py", "w") as f:
            f.writelines([
                "SERVENT_HOST = \"%s\"\n" % comm.SERVENT_HOST,
                "BOOTSTRAP_HOST = \"%s\"\n" % comm.BOOTSTRAP_HOST,
                "BOOTSTRAP_PORT = %d\n" % comm.BOOTSTRAP_PORT,
                "CPANEL_HOST = \"%s\"\n" % comm.CPANEL_HOST,
                "CPANEL_PORT = %d\n" % comm.CPANEL_PORT,
                "ENABLE_CPANEL = %s\n" % ("True" if comm.ENABLE_CPANEL else "False")
            ])

    def user_cpanel_pause(self, _):
        self.send_cpanel_command("pause")

    def user_cpanel_resume(self, _):
        self.send_cpanel_command("resume")


def set_defaults(the_app):
    the_app.setEntry("Num servents", "3")
    the_app.setEntry("n", "3")
    the_app.setEntry("r", "0.5")
    the_app.setEntry("w", "5000")
    the_app.setEntry("h", "5000")
    the_app.setEntry("job_id", "1:1")

    the_app.setEntry("BS host", comm.BOOTSTRAP_HOST)
    the_app.setEntry("BS port", comm.BOOTSTRAP_PORT)
    the_app.setEntry("CP host", comm.CPANEL_HOST)
    the_app.setEntry("CP port", comm.CPANEL_PORT)
    the_app.setEntry("Servent host", comm.SERVENT_HOST)
    the_app.setEntry("Servent start port", START_PORT)
    the_app.setCheckBox("CPanel", comm.ENABLE_CPANEL)


def main():
    app = gui()
    i = Interface(app)

    app.startTabbedFrame("TabbedFrame", 0, sticky="NW")
    app.startTab("Options")
    row = 0
    app.addLabel("title", "Welcome to CHAOS", row=row, column=0, colspan=12)
    row += 1  # ----
    app.addLabelEntry("BS host", row=row, column=0, colspan=4)
    app.addLabelEntry("BS port", row=row, column=4, colspan=4)
    app.addLabelEntry("CP host", row=row, column=8, colspan=4)
    row += 1  # ----
    app.addLabelEntry("CP port", row=row, column=0, colspan=4)
    app.addLabelEntry("Servent host", row=row, column=4, colspan=4)
    app.addLabelEntry("Servent start port", row=row, column=8, colspan=4)
    row += 1  # ----
    app.addCheckBox("CPanel", row=row, column=0, colspan=1)
    app.addButton("Confirm changes", i.user_settings_changed, row=row, column=10, colspan=2)

    app.stopTab()
    app.startTab("Start")
    row = 0
    app.addLabel("title2", "Welcome to CHAOS", row=row, column=0, colspan=12)
    row += 1  # ----
    app.addHorizontalSeparator(row=row, column=1, colour="grey")
    app.addButton("Start Bootstrap server", i.user_start_bootstrap, row=row, column=2, colspan=2)
    app.addHorizontalSeparator(row=row, column=4, colour="grey")
    app.addNumericLabelEntry("Num servents", row=row, column=5, colspan=2)
    app.addButton("Start servents", i.user_start_servents, row=row, column=7, colspan=5)
    row += 1  # ----
    app.addHorizontalSeparator(row=row, column=0, colspan=12, colour="blue")
    row += 1  # ----
    app.addLabel("communicate", "Communicate with local servents (via stdin)", row=row, column=0, colspan=12)
    row += 1  # ----
    app.addLabel("servent_port", "Servent port:", row=row, column=0, colspan=4)
    app.addNumericEntry("port", row=row, column=4, colspan=8)
    row += 1  # ----
    app.addNumericLabelEntry("n", row=row, column=0, colspan=2)
    app.addNumericLabelEntry("r", row=row, column=2, colspan=2)
    app.addNumericLabelEntry("w", row=row, column=4, colspan=2)
    app.addNumericLabelEntry("h", row=row, column=6, colspan=2)
    app.addButton("Start job", i.user_job_start, row=row, column=8, colspan=4)
    row += 1  # ----
    app.addLabelEntry("job_id", row=row, column=5, colspan=3)
    app.addButton("Show job", i.user_job_show, row=row, column=8, colspan=2)
    app.addButton("Stop job", i.user_job_stop, row=row, column=10, colspan=2)
    row += 1  # ----
    app.addHorizontalSeparator(row=row, column=0, colspan=12, colour="blue")
    row += 1  # ----
    app.addButton("Pause CPanel", i.user_cpanel_pause, row=row, column=8, colspan=2)
    app.addButton("Resume CPanel", i.user_cpanel_resume, row=row, column=10, colspan=2)
    row += 1  # ----
    app.addHorizontalSeparator(row=row, column=0, colspan=12, colour="blue")
    row += 1  # ----
    app.addScrolledTextArea("output", row=row, column=0, colspan=12, rowspan=12)

    app.stopTab()
    app.stopTabbedFrame()

    app.setTabbedFrameSelectedTab("TabbedFrame", "Start")

    set_defaults(app)
    app.setStopFunction(i.user_quit)
    app.go()


if __name__ == '__main__':
    main()
