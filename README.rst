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
  This one requires ``terminal-notifier`` on OSX or ``notify-send`` on freedesktop capable systems (e.g linux, *BSD)
