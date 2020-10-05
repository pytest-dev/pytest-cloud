Distributed tests planner plugin for pytest testing framework
=============================================================

.. image:: https://img.shields.io/pypi/v/pytest-cloud.svg
   :target: https://pypi.python.org/pypi/pytest-cloud
.. image:: https://img.shields.io/pypi/pyversions/pytest-cloud.svg
  :target: https://pypi.python.org/pypi/pytest-cloud
.. image:: https://img.shields.io/coveralls/pytest-dev/pytest-cloud/master.svg
   :target: https://coveralls.io/r/pytest-dev/pytest-cloud
.. image:: https://travis-ci.org/pytest-dev/pytest-cloud.svg?branch=master
    :target: https://travis-ci.org/pytest-dev/pytest-cloud
.. image:: https://readthedocs.org/projects/pytest-cloud/badge/?version=latest
    :target: https://readthedocs.org/projects/pytest-cloud/?badge=latest
    :alt: Documentation Status


Install pytest-cloud
--------------------

::

    pip install pytest-cloud

    # install GNU parallel utility
    # https://www.gnu.org/software/parallel/
    # for MacOS, you can use:
    brew install parallel


.. _pytest: http://pytest.org
.. _pytest-xdist: https://pypi.python.org/pypi/pytest-xdist


Features
--------

The plugin provides an easy way of running tests among several test nodes (workers).
Uses the great pytest-xdist_ plugin for actual distributed run.
When used, it will automatically detect capabilites of given node(s) and run only the number of test processes it is
able to handle. If will also filter out offline nodes or nodes which were failed to respond to the
capabilities acquisition call.

Supports automatic codebase propagation to the test nodes, so you don't have to install python dependencies
for your project on remote test nodes globally - just make sure that your virtualenv folder is `inside`
your project folder - that's a requirement.
It will also detect a root folder of the test environment (project root), and will `rsync` it to all test nodes.

NOTE:
> `pytest-cloud` uses `virtualenv` instead of built-in `venv` package.


ATM only ssh transport is supported. So ensure that you have at least public key auth enabled to your test nodes
from the master node (where py.test is executed).


Command-line options
--------------------

* `--cloud-node`
    Node hostname (or user@hostname) to run tests on. Multiple allowed.

* `--cloud-nodes`
    Space-separated list of node hostname (or user@hostname) to run tests on. Multiple allowed.

* `--cloud-python`
    Optional python executable name to be used on the remote test nodes.
    Default is the executable name used for the test run on the master.

* `--cloud-chdir`
    Optional relative path to be used on the remote test nodes as target folder for syncing file and run tests.
    Default is `pytest_<username>_<current_folder_name>`.

* `--cloud-virtualenv-path`
    Optional relative path to the virtualenv to be used on the remote test nodes. By default it will try to detect
    whether current test process is using virtualenv and if it's located inside of the current directory. If that's
    the case, it will use it for rsync on the remote node(s).

* `--cloud-mem-per-process`
    Optional amount of memory roughly needed for test process, in megabytes.
    Will be used to calculate amount of test processes per node, getting the free memory, dividing it for the memory
    per process needed, and getting the minimum of that value and the number of CPU cores of the test node.

* `--cloud-max-processes`
    Optional maximum number of processes per test node. Overrides from above the calculated number
    of processes using memory and number of CPU cores.

* `--cloud-rsync-bandwidth-limit`
    Optional bandwidth limit per `rsync` process, in kilobytes per second. 5000 by default.

* `--cloud-rsync-max-processes`
    Optional process count limit for `rsync` processes. By default there's no limit so rsyncing will be in parallel
    for all test nodes.

* `--cloud-rsync-cipher`
    Optional ssh cipher selection for `rsync` processes. aes128-gcm@openssh.com by default.
    Default cipher is chosen to have the least possible network overhead. Network overhead is system, compilation
    and CPU architecture dependent, however chosen cipher is showing good results in majority of use cases.

Ini file options
----------------

* `cloud_develop_eggs`
    Optional list of python package paths to install in development mode on remote side. Required to be inside of the
    project root directory.


Example
-------

.. code-block:: sh

    py.test tests/ --cloud-node=10.0.120.{1..40} --cloud-mem-per-process=1000 --rsyncdir=.

Or if you pass list of nodes as space-separated list:

.. code-block:: sh

    py.test tests/ --cloud-nodes='10.0.120.1 10.0.120.2' --cloud-mem-per-process=1000 --rsyncdir=.


Contact
-------

If you have questions, bug reports, suggestions, etc. please create an issue on
the `GitHub project page <http://github.com/pytest-dev/pytest-cloud>`_.


License
-------

This software is licensed under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_

See `License file <https://github.com/pytest-dev/pytest-cloud/blob/master/LICENSE.txt>`_


© 2015 Anatoly Bubenkov and others.
