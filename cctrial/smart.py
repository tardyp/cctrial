import sys
import types
import inspect
import StringIO
from importlib import import_module
from twisted.trial import runner

from unittest import TestSuite, TestCase


class SmartDB(object):
    def __init__(self, suite):
        self.testsPerFile = {}
        self.importsPerFile = {}
        self.testsDefinedPerFile = {}
        self.modulePerFile = {}

        # remove any DeprecationWarnings due to inspect
        old_stderr = sys.stderr
        sys.stderr = StringIO.StringIO()
        try:
            self.buildSmartDB(suite)
        finally:
            sys.stderr = old_stderr

    def stripPyc(self, fn):
        if fn.endswith(".pyc"):
            fn = fn[:-1]
        return fn

    def addTestForFile(self, fn, test):
        self.testsPerFile.setdefault(fn, set()).add(test)

    def addTestDefinedForFile(self, fn, test):
        self.testsDefinedPerFile.setdefault(fn, set()).add(test)

    def getImportsForModule(self, m):
        fn = self.stripPyc(m.__file__)
        if fn in self.importsPerFile:
            return self.importsPerFile[fn]
        self.modulePerFile[fn] = m
        importedFiles = set([fn])
        for imports in dir(m):
            f = self.findFile(getattr(m, imports))
            if f and '/lib/' not in f:
                importedFiles.add(f)

        self.importsPerFile[fn] = importedFiles
        return importedFiles

    def findFile(self, o):
        m = dict(inspect.getmembers(o))
        if '__module__' in m:
            m = import_module(m['__module__'])
            fn = self.stripPyc(m.__file__)
            self.modulePerFile[fn] = m
            return fn
        if '__file__' in m:
            return self.stripPyc(m['__file__'])

    def buildSmartDB(self, suite):
        for test in iter(suite):
            if isinstance(test, TestSuite):
                self.buildSmartDB(test)
            elif isinstance(test, TestCase):
                for parent in test._parents:
                    if isinstance(parent, types.ModuleType):
                        self.addTestDefinedForFile(self.stripPyc(parent.__file__), test)
                        for fn in self.getImportsForModule(parent):
                            self.addTestForFile(fn, test)

    def printDB(self):
        for fn, tests in self.testsPerFile.items():
            print fn
            print "    " + "\n    ".join([test.id() for test in tests])

    def reloadFile(self, fn):
        # remove tests defined by this file from imported files
        tests_to_remove = self.testsPerFile[fn]
        for imported_fn in self.importsPerFile[fn]:
            self.testsPerFile[imported_fn] -= tests_to_remove

        del self.importsPerFile[fn]
        del self.testsPerFile[fn]

        # reload the module
        module = self.modulePerFile[fn]
        reload(module)

        # use trial's testrunner to discover the tests
        loader = runner.TestLoader()
        suite = loader.loadByNames([module.__name__], True)
        # reinject them in the db
        self.buildSmartDB(suite)

    def getSuiteForModifiedFiles(self, modifiedFiles):
        tests = set()
        for fn in modifiedFiles:
            if fn in self.testsDefinedPerFile:
                self.reloadFile(fn)
            elif fn in self.modulePerFile:
                # reload the module to make sure the stacktraces are correct
                reload(self.modulePerFile[fn])
            if fn in self.testsPerFile:
                tests.update(self.testsPerFile[fn])
        if tests:
            return TestSuite(tests)
