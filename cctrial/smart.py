import sys
import types
import traceback
import os
import pkgutil
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
        fn = self.stripPyc(inspect.getfile(m))
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
            try:
                fn = self.stripPyc(inspect.getfile(m))
            except TypeError: # builtin modules don't have a file
                return None
            self.modulePerFile[fn] = m
            return fn
        if '__file__' in m:
            return self.stripPyc(m['__file__'])

    def findModuleForTestCase(self, test):
        if hasattr(test, "_parents"):
            for parent in test._parents:
                if isinstance(parent, types.ModuleType):
                    return parent
        else:
            return import_module(type(test).__module__)

    def buildSmartDB(self, suite):
        for test in iter(suite):
            if isinstance(test, TestSuite):
                self.buildSmartDB(test)
            elif isinstance(test, TestCase):
                module = self.findModuleForTestCase(test)
                if module is not None:
                    self.addTestDefinedForFile(self.stripPyc(inspect.getfile(module)), test)
                    for fn in self.getImportsForModule(module):
                        self.addTestForFile(fn, test)
            elif isinstance(test, runner.ErrorHolder):
                print "!!! unable to load", test.description, ":", test.error[1]
                tb = test.error[2]
                traceback.print_tb(tb)
            else:

                print test

    def printDB(self):
        for fn, tests in self.testsPerFile.items():
            print fn
            print "    " + "\n    ".join([test.id() for test in tests])

    def getModuleForFile(self, fn):
        module = self.modulePerFile.get(fn)
        if module is None:
            for importer, name, ispkg in pkgutil.iter_modules():
                if fn.startswith(importer.path):
                    fn = fn[len(importer.path):-3]
                    fn = fn.strip("/")
                    module_name = ".".join(fn.split(os.sep))
                    try:
                        module = __import__(module_name)
                    except ImportError:
                        traceback.print_exc()
                    break
        return module

    def reloadFile(self, fn):
        # remove tests defined by this file from imported files
        if fn in self.importsPerFile:
            tests_to_remove = self.testsPerFile.get(fn, [])
            for imported_fn in self.importsPerFile.get(fn, []):
                self.testsPerFile[imported_fn] -= tests_to_remove

            del self.importsPerFile[fn]
            del self.testsPerFile[fn]

        # reload the module
        module = self.getModuleForFile(fn)
        if module is None:
            return
        try:
            reload(module)
        except Exception:
            traceback.print_exc()

        # use trial's testrunner to discover the tests
        loader = runner.TestLoader()
        suite = loader.loadByNames([module.__name__], True)
        # reinject them in the db
        self.buildSmartDB(suite)

    def getSuiteForModifiedFiles(self, modifiedFiles):
        tests = set()
        for fn in modifiedFiles:
            if os.path.basename(fn).startswith("test_"):
                self.reloadFile(fn)
            elif fn in self.modulePerFile:
                # reload the module to make sure the stacktraces are correct
                try:
                    reload(self.modulePerFile[fn])
                except Exception:
                    traceback.print_exc()
            if fn in self.testsPerFile:
                tests.update(self.testsPerFile[fn])
        if tests:
            return TestSuite(tests)
