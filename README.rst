Splinter plugin for the py.test runner
======================================

.. image:: https://api.travis-ci.org/pytest-dev/pytest-cloud.png
    :target: https://travis-ci.org/pytest-dev/pytest-cloud
.. image:: https://pypip.in/v/pytest-cloud/badge.png
    :target: https://crate.io/packages/pytest-cloud/
.. image:: https://coveralls.io/repos/pytest-dev/pytest-cloud/badge.png?branch=master
    :target: https://coveralls.io/r/pytest-dev/pytest-cloud
.. image:: https://readthedocs.org/projects/pytest-cloud/badge/?version=latest
    :target: https://readthedocs.org/projects/pytest-cloud/?badge=latest
    :alt: Documentation Status


Install pytest-cloud
-----------------------

::

    pip install pytest-cloud


.. _pytest: http://pytest.org
.. _pytest-xdist: https://pypi.python.org/pypi/pytest-xdist


Features
--------

The plugin provides an easy way of running tests amoung several test nodes (slaves).
Uses the great pytest-xdist_ plugin for actual distributed run.
When used, it will automatically detect capabilites of given node(s) and run only the number of test processes it is
able to handle.
ATM only ssh transport is supported. So ensure that you have at least public key auth enabled to your test nodes
from the master node (where py.test is executed).


Command-line options
--------------------

* `--cloud-node`
    Node host name to run tests on. Multiple allowed.


Example
-------

.. code-block:: sh

    py.test tests --cloud-node=10.0.120.{1..40}


Contact
-------

If you have questions, bug reports, suggestions, etc. please create an issue on
the `GitHub project page <http://github.com/pytest-dev/pytest-cloud>`_.


License
-------

This software is licensed under the `MIT license <http://en.wikipedia.org/wiki/MIT_License>`_

See `License file <https://github.com/pytest-dev/pytest-cloud/blob/master/LICENSE.txt>`_


© 2015 Anatoly Bubenkov and others.
