import argh
import shutil
import os
import linecache

from unittest import TestSuite
from twisted.trial import runner
from twisted.internet import reactor
from twisted.internet import defer

from .runner import Runner
from .smart import SmartDB
from .reporter import Reporter
from .watcher import PythonFileWatcher
from .watcher import GitFileWatcher
from .notify import notify


class CCTrial(object):

    def __init__(self, opts):
        self.opts = opts
        if opts.smart:
            opts.forever = True
        if opts.hook:
            opts.smart = True
            self.watcher = GitFileWatcher(self.wake)
        else:
            self.watcher = PythonFileWatcher(self.wake, opts.cwd)
        loader = runner.TestLoader()
        suite = loader.loadByNames(opts.test_names, True)

        self.fullSuite = self.filterSuite(suite, opts.grep)
        self.smartSuite = self.retrySuite = self.retryTest = None

        if self.opts.verbose:
            for test in self.fullSuite:
                print test.id()

        self.smartDB = SmartDB(self.fullSuite)
        self.running = False
        # smartDB.printDB()

    def filterSuite(self, suite, grep):
        tests = []
        for test in iter(suite):
            if isinstance(test, TestSuite):
                tests.extend(iter(self.filterSuite(test, grep)))
            elif grep is None or grep in test.id():
                tests.append(test)
        return TestSuite(tests)

    def prepareRun(self):
        if os.path.exists("_trial_temp"):
            shutil.rmtree("_trial_temp")
        Reporter.numTests = self.fullSuite.countTestCases()
        self.trial = Runner(Reporter, self.opts.jobs, [])
        self.trial.prepareRun()

    def getNextSuite(self):
        if self.retryTest is not None:
            return self.retryTest
        if self.retrySuite is not None:
            return self.retrySuite
        if self.opts.smart:
            if self.smartSuite is None:
                print "no test detected for this file..."
                return None
            return self.smartSuite
        return self.fullSuite

    def isBigSuite(self):
        return self.suite is self.fullSuite or self.suite is self.smartSuite

    def onPass(self):
        """decide what to do if the current suite is passed
        @return True if if should re-run without waiting
        """
        notify("%d tests run" % (self.suite.countTestCases()),
               "everything good!", True)
        shouldReRun = False
        if self.retryTest is self.suite:
            self.retryTest = None
            shouldReRun = True
            if self.retrySuite.countTestCases() == 1:
                self.retrySuite = None
        elif self.retrySuite is self.suite:
            self.retrySuite = None
            shouldReRun = True

        if not self.opts.forever and self.isBigSuite():
            reactor.stop()
        return shouldReRun

    def onFail(self, retry, biggest_problem):
        """decide what to do if the current suite is failed
        @return True if if should re-run without waiting
        """
        if self.isBigSuite():
            notify("%d tests run" % (self.suite.countTestCases()),
                   "%d tests broken!" % (len(retry)), False)
        elif self.suite is self.retrySuite:
            notify("%d fixed" % (self.suite.countTestCases() - len(retry)),
                   "%d tests failures to fix" % (len(retry)), False)
        else:
            biggest_problem_id = "?"
            if biggest_problem:
                biggest_problem_id = biggest_problem.id()
            notify("Still broken!", biggest_problem_id, False)
            for log in ["test", "out", "err"]:
                fn = "_trial_temp/0/%s.log" % (log,)
                if os.path.exists(fn):
                    print fn, ":"
                    with open(fn) as f:
                        print f.read()
            return False
        retry = sorted(retry)
        self.retrySuite = TestSuite(retry)
        if biggest_problem:
            self.retryTest = TestSuite([biggest_problem])
            return True

    @defer.inlineCallbacks
    def runOneSuite(self):
        """ run one suite
        @return True if if should re-run without waiting
        """
        self.suite = self.getNextSuite()
        if self.suite is None:
            defer.returnValue(False)
        # clear cache for stacktraces
        linecache.clearcache()
        result = yield self.trial.run(self.suite)
        result = result.original
        retry = result.getRetrySuite()
        if not retry:
            defer.returnValue(self.onPass())
        else:
            defer.returnValue(self.onFail(retry, result.biggest_problem))

    def run(self):
        if self.fullSuite.countTestCases() == 0:
            print "no test selected"
            reactor.callLater(0, reactor.stop)
            return

        if self.opts.hook:
            self.smartSuite = self.smartDB.getSuiteForModifiedFiles(self.watcher.modified_files)
            if self.smartSuite is None:
                print "no test to run"
                reactor.callLater(0, reactor.stop)
                return
        self.prepareRun()
        if not self.opts.smart or self.opts.hook:
            self.wake()
        else:
            print "waiting for filesystem changes..."
        self.maybeWait()

    def maybeWait(self):
        if reactor.running:
            print "waiting for filesystem changes..."

    @defer.inlineCallbacks
    def wake(self):
        if self.running:
            return

        if self.watcher.modified_files:
            self.smartSuite = self.smartDB.getSuiteForModifiedFiles(self.watcher.modified_files)
            if self.retryTest is None:
                self.watcher.reset()

        self.running = True
        try:
            while self.running:
                self.running = yield self.runOneSuite()
                self.prepareRun()
        finally:
            self.running = False
        self.maybeWait()


@argh.arg('test_names', nargs='+')
@argh.arg('-f', '--forever', help="run forever even if all tests are passed", default=False)
@argh.arg('-j', '--jobs', help="number of cpu to use", type=int, default=1)
@argh.arg('-g', '--grep', help="filter the tests", default=None)
@argh.arg('-v', '--verbose', help="list all tests run", action="store_true", default=False)
@argh.arg('-s', '--smart', help="Smart runs. Run only tests affected by modified file", action="store_true")
@argh.arg('-c', '--cwd', help="only watch current directory (not all directories in development)", default=False)
@argh.arg('-H', '--hook', help="run tests for files just committed", default=False)
@argh.expects_obj
def cctrial(opts):
    CCTrial(opts).run()
    reactor.run()


def main():
    argh.dispatch_command(cctrial)
