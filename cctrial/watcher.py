import os
import pkgutil
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

        self.observer.start()

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
