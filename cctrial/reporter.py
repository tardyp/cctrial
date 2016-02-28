import os
import sys

from twisted.trial.reporter import TreeReporter
from twisted.trial.reporter import Reporter as TrialReporter


class Reporter(TreeReporter):
    curtest = None
    biggest_problem_len = 0
    biggest_problem = None
    # For non-TTY output: is cursor at the beginning of the current line.
    at_line_start = True

    def writepad(self, s, p, color=None):
        if not os.isatty(sys.stdout.fileno()):
            color = None
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

    @staticmethod
    def isTTY():
        return os.isatty(sys.stdout.fileno())

    def writeStatusString(self):
        self.writepad(self.stripid(self.curtest.id(), 70), 70)
        self.writepad(" % 5d/% 5d" % (self.testsRun, self.numTests), 12)
        self.writepad(" % 5dF" % (len(self.failures)), 12, self.failures and self.FAILURE or None)
        self.writepad(" % 5dE" % (len(self.errors)), 12, self.errors and self.ERROR or None)
        self.writepad(" % 5dS" % (len(self.skips)), 12, self.skips and self.SKIP or None)
        self.writepad(" % 5dT" % (len(self.expectedFailures)), 12)
        self.writepad(" % 5d!" % (len(self.unexpectedSuccesses)), 12,
                      self.unexpectedSuccesses and self.ERROR or None)

    def updateLine(self):
        if self.curtest is None:
            return
        if not self.isTTY():
            if not self.at_line_start:
                # Some dots were outputted, need to start new line.
                self._write("\n")
            self.writeStatusString()
            self._write("\n")
            self.at_line_start = True
        else:
            self._write("\r")
            self.writeStatusString()

    def addSuccess(self, test):
        TrialReporter.addSuccess(self, test)
        if os.isatty(sys.stdout.fileno()):
            self.updateLine()
        else:
            self._write(".")
            self.at_line_start = False

    def addError(self, *args):
        TrialReporter.addError(self, *args)
        self.updateLine()

    def addFailure(self, *args):
        TrialReporter.addFailure(self, *args)
        self.updateLine()

    def addSkip(self, *args):
        TrialReporter.addSkip(self, *args)
        self.updateLine()

    def addExpectedFailure(self, *args):
        TrialReporter.addExpectedFailure(self, *args)
        self.updateLine()

    def addUnexpectedSuccess(self, *args):
        TrialReporter.addUnexpectedSuccess(self, *args)
        self.updateLine()

    def startTest(self, test):
        TrialReporter.startTest(self, test)
        self.curtest = test
        if os.isatty(sys.stdout.fileno()):
            self.updateLine()

    def _printResults(self, flavor, errors, formatter):
        for reason, cases in sorted(self._groupResults(errors, formatter), key=lambda x: len(x[1])):
            self._write(self._doubleSeparator)
            self._write(" %d case%s: " % (len(cases), len(cases) > 1 and "s" or ""))
            if "ERROR" in flavor or "FAIL" in flavor:
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
        if self.isTTY():
            self._write("\r" + " " * 150 + "\n")
        elif not self.at_line_start:
            self._write("\n")
        TreeReporter.done(self)
        self.updateLine()
        self._write("\n")

    def getRetrySuite(self):
        res = set()
        for e in self.errors:
            res.add(e[0])
        for e in self.failures:
            res.add(e[0])
        return res
