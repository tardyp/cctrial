cctrial
=======

cctrial is a tool for using twisted trial in a continuous manner.

cctrial will re-run failed tests until all succeed.

cctrial is designed for a specific workflow, which helps doing big refactors that break lots of tests.

cctrial is not designed to replace trial, for all other usecases.

Installation
------------

Install cctrial in your virtualenv:

.. code-block:: bash

    pip install cctrial

Workflow description
--------------------

Run:

.. code-block:: bash

    cctrial -j2 -f my.package

It will monitor all the directories where packages are installed with ``pip install -e`` or ``./setup.py develop``.
The re-runs will only happen after a file has been modified in one of the watched directories.

- Run the full unit test suite.

- Gather all the broken tests, if any.

- Re-run the test which failure appears the most.
  In cctrial workflow, you always fix tests one by one, starting by the tests whose resolution will probably fix the most errors.

- When current test finally pass, will re-run all tests that originally failed.

- After all tests pass, will re-run the full test suite

Additional features
-------------------

- Custom reporter designed to concentrate information as much as possible in the terminal screen.

- During the run, always updating one line status, tells you the current test, number of failures, etc.

- After the run, summarized issues are printed

- Only during the fix test loop, logs for the current testcase are printed, as well as the failure details, and stdout/stderr of testcase.

- Desktop notification support.
  This one requires ``terminal-notifier`` on OSX or ``notify-send`` on freedesktop capable systems (e.g linux, xBSD).

Screenshots
-----------

.. code-block:: text

    % cctrial buildbot.test.regressions
    Running 38 tests.


    -------------------------------------------------------------------------------
    Ran 38 tests in 1.400s

    PASSED (successes=38)
    buildbot.test.regressions.test_unpickling.StatusPickles.test_upgrade      38/   38     0F          0E          0S          0T          0!
    waiting for filesystem change...


After introducing a bug:

.. code-block:: text

    Running 38 tests.


    =============================================================================== 4 cases: [ERROR]
    Traceback (most recent call last):
      File "/Users/ptardy/dev/bb/buildbot-heroku/buildbot/master/buildbot/test/regressions/test_import_unicode_changes.py", line 31, in make_dbc
        self.db = DBConnector(master, self.basedir)
    exceptions.TypeError: __init__() takes exactly 2 arguments (3 given)

    -------------------------------------------------------------------------------
    Ran 38 tests in 0.272s

    FAILED (errors=4, successes=34)
    buildbot.test.regressions.test_unpickling.StatusPickles.test_upgrade      38/   38     0F          4E          0S          0T          0!
    re-run: testAsciiChange (buildbot.test.regressions.test_import_unicode_changes.TestUnicodeChanges)
    Running 1 tests.


    =============================================================================== 1 case: [ERROR]
    Traceback (most recent call last):
      File "/Users/ptardy/dev/bb/buildbot-heroku/buildbot/master/buildbot/test/regressions/test_import_unicode_changes.py", line 31, in make_dbc
        self.db = DBConnector(master, self.basedir)
    exceptions.TypeError: __init__() takes exactly 2 arguments (3 given)

    -------------------------------------------------------------------------------
    Ran 1 tests in 0.001s

    FAILED (errors=1)

    Logs: Log opened.
    --> buildbot.test.regressions.test_import_unicode_changes.TestUnicodeChanges.testAsciiChange <--
    cleaning database sqlite://
    Main loop terminated.



    please fix: testAsciiChange (buildbot.test.regressions.test_import_unicode_changes.TestUnicodeChanges)
    waiting for filesystem change...

After fixing the bug:

.. code-block:: text

    re-run: testAsciiChange (buildbot.test.regressions.test_import_unicode_changes.TestUnicodeChanges)
    Running 1 tests.


    -------------------------------------------------------------------------------
    Ran 1 tests in 0.001s

    PASSED (successes=1)

    Running 4 tests.


    -------------------------------------------------------------------------------
    Ran 4 tests in 0.610s

    PASSED (successes=4)
    buildbot.test.regressions.test_import_unicode_changes                      4/    4     0F          0E          0S          0T          0!

    Running 38 tests.


    -------------------------------------------------------------------------------
    Ran 38 tests in 1.400s

    PASSED (successes=38)
    buildbot.test.regressions.test_unpickling.StatusPickles.test_upgrade      38/   38     0F          0E          0S          0T          0!
    waiting for filesystem change...


Design Notes
------------

Problem with re-running tests is that you cannot reuse the same python environment.
Using builtin 'reload' is really something you want to avoid.

cctrial uses DistTrialRunner in order to implement the reload.
The workers leave in a separate python environment and are re-spawn between runs.

In order to optimize startup time:

- We prepare the workers while waiting for the filesystem change.
  ``import twisted.internet.reactor`` takes 600ms.

- We discover the tests only once
  test discovery for buildbot takes 2160ms
