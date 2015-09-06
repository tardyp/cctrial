import os
import sys

import pkgutil
from subprocess import check_output
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from twisted.internet import reactor


class PythonFileWatcher(FileSystemEventHandler):
    modified_files = set()

    def __init__(self, wake_cb, only_cwd):
        self.wake_cb = wake_cb
        FileSystemEventHandler.__init__(self)
        self.observer = Observer()
        if only_cwd:
            self.observePythonDirs(os.getcwd())
        else:
            for importer, name, ispkg in pkgutil.iter_modules():
                if ispkg and '/lib/' not in importer.path:
                    self.observePythonDirs(importer.path)
        try:
            self.observer.start()
        except OSError as e:
            # clearer error for linux
            if "inotify watch limit reached" in e:
                print e
                print "you should increase the inotify quotas"
                print
                print "   sudo sysctl fs.inotify.max_user_watches=100000"
                print "   sudo sh -c 'echo fs.inotify.max_user_watches=100000>>/etc/sysctl.conf'"
                sys.exit(1)
            else:
                raise

    def observePythonDirs(self, path):
        self.observer.schedule(self, path, True)

    def _on_modified(self, path):
        self.modified_files.add(path)
        self.wake_cb()

    def on_modified(self, e):
        if e.src_path.endswith(".py"):
            print e.src_path
            # watchdog works with threads (omg!), so we must call the callback in the mainthread
            reactor.callFromThread(self._on_modified, e.src_path)

    def reset(self):
        self.modified_files = set()

    def stop(self):
        self.observer.stop()
        self.observer.join()


class GitFileWatcher(object):
    modified_files = set()

    def __init__(self, wake_cb):
        basedir = os.getcwd()
        for line in check_output(["git", "diff", "--name-only", "--stat", "HEAD~"]).splitlines():
            if line.endswith(".py"):
                self.modified_files.add(os.path.join(basedir, line))

    def reset(self):
        self.modified_files = set()

    def stop(self):
        pass
