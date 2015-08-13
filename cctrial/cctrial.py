import argh
import shutil
import os

from unittest import TestSuite
from twisted.trial import runner

from .runner import Runner
from .smart import SmartDB
from .reporter import Reporter
from .watcher import PythonFileWatcher
from .notify import notify
from .reactor import FakeReactor


class CCTrial(object):

    def __init__(self, opts):
        self.opts = opts
        if opts.smart:
            opts.forever = True
        self.reactor = FakeReactor()
        self.watcher = PythonFileWatcher(self.reactor.wake)
        loader = runner.TestLoader()
        suite = loader.loadByNames(opts.test_names, True)

        self.fullSuite = self.filterSuite(suite, opts.grep)
        self.smartSuite = self.retrySuite = self.retryTest = None

        if self.opts.verbose:
            for test in self.fullSuite:
                print test.id()

        self.smartDB = SmartDB(self.fullSuite)
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
        self.trial.prepareRun(reactor=self.reactor)

    def wait(self):
        while not self.watcher.modified_files:
            self.reactor.wait()
        self.smartSuite = self.smartDB.getSuiteForModifiedFiles(self.watcher.modified_files)
        self.watcher.reset()

    def getNextSuite(self):
        if self.retryTest is not None:
            return self.retryTest
        if self.retrySuite is not None:
            return self.retrySuite
        if self.opts.smart:
            if self.smartSuite is None:
                print "no test detected for this file..."
                return None
        return self.fullSuite

    def onPass(self):
        notify("%d tests run" % (self.suite.countTestCases()),
               "everything good!")

        if self.retryTest is not None:
            self.retryTest = None
        elif self.retrySuite is not None:
            self.retrySuite = None

        if self.opts.forever:
            if self.suite == self.fullSuite:
                return True
            else:
                return False

        elif self.suite == self.fullSuite:
            self.done = True

    def onFail(self, retry, biggest_problem):
        if self.suite == self.fullSuite:
            notify("%d tests run" % (self.suite.countTestCases()),
                   "%d tests broken!" % (len(retry)))
        elif self.suite == self.retrySuite:
            notify("%d fixed" % (self.suite.countTestCases() - len(retry)),
                   "%d tests failures to fix" % (len(retry)))
        else:
            notify("Still broken!", biggest_problem.id())
            print "Logs:",
            for log in ["test", "out", "err"]:
                with open("_trial_temp/0/%s.log" % (log,)) as f:
                    print f.read()

        retry = sorted(retry)
        self.retrySuite = TestSuite(retry)
        self.retryTest = TestSuite([biggest_problem])

    def runOneSuite(self):
        if self.suite is None:
            return True
        result = self.trial.run(self.suite).original
        # already prepare the next run
        self.prepareRun()
        retry = result.getRetrySuite()
        if not retry:
            return self.onPass()
        else:
            self.onFail(retry, result.biggest_problem)
            return True

    def run(self):
        if self.fullSuite.countTestCases() == 0:
            print "no test selected"
            return

        self.prepareRun()
        if self.opts.smart:
            self.wait()

        self.done = False
        while not self.done:
            self.suite = self.getNextSuite()
            if self.runOneSuite():
                self.wait()

        self.watcher.stop()


@argh.arg('test_names', nargs='+')
@argh.arg('-f', '--forever', help="run forever even if all tests are passed", default=False)
@argh.arg('-j', '--jobs', help="number of cpu to use", type=int, default=1)
@argh.arg('-g', '--grep', help="filter the tests", default=None)
@argh.arg('-v', '--verbose', help="list all tests run", action="store_true", default=False)
@argh.arg('-s', '--smart', help="Smart runs. Run only tests affected by modified file", action="store_true")
@argh.expects_obj
def cctrial(opts):
    CCTrial(opts).run()


def main():
    argh.dispatch_command(cctrial)
