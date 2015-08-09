import pkgutil
import argh
import shutil
import os
import sys
notify = lambda _, __: None
if sys.platform == 'darwin':
    try:
        from .osx import notify
    except ImportError:
        pass
elif sys.platform != 'win32':
    try:
        from .freedesktop import notify
    except ImportError:
        pass

from unittest import TestSuite

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from twisted.trial.reporter import TreeReporter, Reporter
from twisted.trial import runner
from twisted.internet import reactor
from .runner import Runner


class MyHandler(FileSystemEventHandler):
    def on_modified(self, e):
        if e.src_path.endswith(".py"):
            myReactor.wake()


def observe_with(observer, event_handler, pathnames, recursive):
    for pathname in set(pathnames):
        observer.schedule(event_handler, pathname, recursive)
    observer.start()


class MyReactor(object):
    running = False
    waiting = False
    processes = []

    def run(self):
        self.running = True
        while self.running:
            reactor.iterate()

    def wait(self):
        print "waiting for filesystem change..."
        self.waiting = True
        while self.waiting:
            reactor.iterate(0.1)

    def stop(self):
        self.running = False
        # kill the workers
        for p in self.processes:
            p.signalProcess('TERM')
        self.processes = []

    def wake(self):
        self.waiting = False

    def spawnProcess(self, *a, **kw):
        p = reactor.spawnProcess(*a, **kw)
        self.processes.append(p)
        return p

    def addSystemEventTrigger(self, *a, **kw):
        return reactor.addSystemEventTrigger(*a, **kw)

myReactor = MyReactor()


class MyReporter(TreeReporter):
    def writepad(self, s, p, color=None):
        if len(s) > p:
            s = (u"\u2026" + s[1 + len(s) - p:]).encode("utf-8")
        else:
            s = s + " " * (p - len(s))
        if color:
            self._colorizer.write(s, color)
        else:
            self._stream.write(s)

    def stripid(self, s, p):
        while(len(s) > p) and "." in s:
            s = ".".join(s.split(".")[:-1])
        return s

    def updateLine(self):
        # print update line only in case of big run
        if self.numTests == 1:
            return
        self._write("\r")
        self.writepad(self.stripid(self.curtest.id(), 70), 70)
        self.writepad(" % 5d/% 5d" % (self.testsRun, self.numTests), 12)
        self.writepad(" % 5dF" % (len(self.failures)), 12, self.failures and self.FAILURE or None)
        self.writepad(" % 5dE" % (len(self.errors)), 12, self.errors and self.ERROR or None)
        self.writepad(" % 5dS" % (len(self.skips)), 12, self.skips and self.SKIP or None)
        self.writepad(" % 5dT" % (len(self.expectedFailures)), 12)
        self.writepad(" % 5d!" % (len(self.unexpectedSuccesses)), 12,
                      self.unexpectedSuccesses and self.ERROR or None)

    def addSuccess(self, test):
        Reporter.addSuccess(self, test)
        self.updateLine()

    def addError(self, *args):
        Reporter.addError(self, *args)
        self.updateLine()

    def addFailure(self, *args):
        Reporter.addFailure(self, *args)
        self.updateLine()

    def addSkip(self, *args):
        Reporter.addSkip(self, *args)
        self.updateLine()

    def addExpectedFailure(self, *args):
        Reporter.addExpectedFailure(self, *args)
        self.updateLine()

    def addUnexpectedSuccess(self, *args):
        Reporter.addUnexpectedSuccess(self, *args)
        self.updateLine()

    def startTest(self, test):
        Reporter.startTest(self, test)
        self.curtest = test
        self.updateLine()

    def _printResults(self, flavor, errors, formatter):
        for reason, cases in sorted(self._groupResults(errors, formatter), key=lambda x: len(x[1])):
            self._write(self._doubleSeparator)
            self._write(" %d case%s: " % (len(cases), len(cases) > 1 and "s" or ""))
            if "ERROR" in flavor or "FAILURE" in flavor:
                self._colorizer.write(flavor, self.ERROR)
                self._writeln('')
                if len(cases) > self.biggest_problem_len:
                    self.biggest_problem = cases[0]
            else:
                self._writeln(flavor)
            self._write(reason)
            self._writeln('')

    def done(self):
        self.biggest_problem_len = 0
        self.biggest_problem = None
        self._write("\r" + " " * 150 + "\n")
        TreeReporter.done(self)
        self.updateLine()
        self._write("\n")


def prepareRun(suite, jobs=1):
    if os.path.exists("_trial_temp"):
        shutil.rmtree("_trial_temp")
    MyReporter.numTests = suite.countTestCases()
    trial = Runner(MyReporter, jobs, [])
    trial.prepareRun(reactor=myReactor)
    return trial


def filterSuite(suite, grep):
    tests = []
    for test in iter(suite):
        if isinstance(test, TestSuite):
            tests.extend(iter(filterSuite(test, grep)))
        elif grep in test.id():
            tests.append(test)
    return TestSuite(tests)


@argh.arg('test_names', nargs='+')
@argh.arg('-f', '--forever', help="run forever even if all tests are passed")
@argh.arg('-j', '--jobs', help="number of cpu to use", type=int)
@argh.arg('-g', '--grep', help="filter the tests")
@argh.arg('-v', '--verbose', help="list all tests run", action="store_true")
def cctrial(test_names, forever=False, jobs=1, grep=None, verbose=False):
    paths = []
    for importer, name, ispkg in pkgutil.iter_modules():
        if ispkg and '/lib/' not in importer.path:
            paths.append(importer.path)

    observer = Observer()
    observe_with(observer, MyHandler(), paths, True)
    loader = runner.TestLoader()
    suite = loader.loadByNames(test_names, True)
    if grep is not None:
        suite = filterSuite(suite, grep)
    initial_suite = suite
    if verbose:
        for test in suite:
            print test.id()
    trial = prepareRun(suite, jobs)
    while True:
        result = trial.run(suite)
        to_retry = set()
        for e in result.original.errors:
            to_retry.add(e[0])
        for e in result.original.failures:
            to_retry.add(e[0])
        if not to_retry:
            notify("%d tests run" % (suite.countTestCases()),
                   "everything good!")
            if forever:
                if suite == initial_suite:
                    wait = True
                else:
                    wait = False
                    suite = initial_suite
                trial = prepareRun(suite, jobs)
                if wait:
                    myReactor.wait()
                continue
            else:
                print "congrats!"
                break
        else:
            if suite == initial_suite:
                notify("%d tests run" % (suite.countTestCases()),
                       "%d tests broken!" % (len(to_retry)))
            else:
                notify("%d fixed" % (suite.countTestCases() - len(to_retry)),
                       "%d tests failures to fix" % (len(to_retry)))
            to_retry = sorted(to_retry)

        test = result.original.biggest_problem
        # re-run forever the test which is among the great majority, and then rerun
        suite = TestSuite(tests=[test])
        trial = prepareRun(suite, 1)
        while True:
            print "re-run:", test
            result = trial.run(suite)
            if not (result.original.errors or result.original.failures):
                break
            print "Logs:",
            for log in ["test", "out", "err"]:
                with open("_trial_temp/0/%s.log" % (log,)) as f:
                    print f.read()
            notify("test failure to fix", test.id())
            print "please fix:", test
            trial = prepareRun(suite, 1)
            myReactor.wait()
        suite = TestSuite(tests=to_retry)
        trial = prepareRun(suite, jobs)
    observer.stop()
    observer.join()


def main():
    argh.dispatch_command(cctrial)
