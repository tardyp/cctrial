import argh
import shutil
import os

from unittest import TestSuite
from twisted.trial import runner
from twisted.internet import reactor
from twisted.internet import defer

from .runner import Runner
from .smart import SmartDB
from .reporter import Reporter
from .watcher import PythonFileWatcher
from .notify import notify


class CCTrial(object):

    def __init__(self, opts):
        self.opts = opts
        if opts.smart:
            opts.forever = True
        self.watcher = PythonFileWatcher(self.wake)
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

    def onPass(self):
        notify("%d tests run" % (self.suite.countTestCases()),
               "everything good!", True)
        if self.retryTest is self.suite:
            self.retryTest = None
            if self.retrySuite.countTestCases() == 1:
                self.retrySuite = None
        elif self.retrySuite is self.suite:
            self.retrySuite = None

        if self.opts.forever:
            if self.suite is self.fullSuite or self.suite is self.smartSuite:
                return False
            else:
                return True

        elif self.suite is self.fullSuite or self.suite is self.smartSuite:
            reactor.stop()

    def onFail(self, retry, biggest_problem):
        if self.suite is self.fullSuite:
            notify("%d tests run" % (self.suite.countTestCases()),
                   "%d tests broken!" % (len(retry)), False)
        elif self.suite is self.retrySuite:
            notify("%d fixed" % (self.suite.countTestCases() - len(retry)),
                   "%d tests failures to fix" % (len(retry)), False)
        else:
            notify("Still broken!", biggest_problem.id(), False)
            for log in ["test", "out", "err"]:
                fn = "_trial_temp/0/%s.log" % (log,)
                print fn, ":"
                with open(fn) as f:
                    print f.read()
            return
        retry = sorted(retry)
        self.retrySuite = TestSuite(retry)
        self.retryTest = TestSuite([biggest_problem])

    @defer.inlineCallbacks
    def runOneSuite(self):
        """ run one suite
        @return True if if should re-run without waiting
        """
        self.suite = self.getNextSuite()
        if self.suite is None:
            defer.returnValue(False)
        result = yield self.trial.run(self.suite)
        result = result.original
        retry = result.getRetrySuite()
        if not retry:
            defer.returnValue(self.onPass())
        else:
            self.onFail(retry, result.biggest_problem)
            defer.returnValue(False)

    def run(self):
        if self.fullSuite.countTestCases() == 0:
            print "no test selected"
            return

        self.prepareRun()
        if not self.opts.smart:
            self.wake()
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
        while self.running:
            self.running = yield self.runOneSuite()
            self.prepareRun()

        print "waiting for filesystem changes..."


@argh.arg('test_names', nargs='+')
@argh.arg('-f', '--forever', help="run forever even if all tests are passed", default=False)
@argh.arg('-j', '--jobs', help="number of cpu to use", type=int, default=1)
@argh.arg('-g', '--grep', help="filter the tests", default=None)
@argh.arg('-v', '--verbose', help="list all tests run", action="store_true", default=False)
@argh.arg('-s', '--smart', help="Smart runs. Run only tests affected by modified file", action="store_true")
@argh.expects_obj
def cctrial(opts):
    CCTrial(opts).run()
    reactor.run()

def main():
    argh.dispatch_command(cctrial)
