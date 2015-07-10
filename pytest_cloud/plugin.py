"""Distributed tests planner plugin for pytest testing framework.

Provides an easy way of running tests amoung several test nodes (slaves).
"""
from __future__ import division
import argparse
import timeout_decorator

try:
    from itertools import filterfalse
except ImportError:
    from itertools import ifilterfalse as filterfalse
from itertools import chain
import math
import os.path
import sys

import execnet
from xdist.slavemanage import (
    NodeManager,
)
from pytest_cache import getrootdir
import six

import pytest

from .rsync import RSync
from . import patches


class SplinterXdistPlugin(object):

    """Plugin class to defer pytest-xdist hook handler."""

    def pytest_configure_node(self, node):
        """Configure node information before it gets instantiated.

        Acivate the virtual env, so the node is able to import dependencies.
        """
        virtualenv_path = node.config.option.cloud_virtualenv_path
        node.gateway.remote_exec(activate_env, virtualenv_path=virtualenv_path).waitclose()


@pytest.mark.trylast
def pytest_configure(config):
    """Register pytest-cloud's deferred plugin."""
    if (
        getattr(config, 'slaveinput', {}).get('slaveid', 'local') == 'local' and
            config.option.cloud_nodes and
            config.pluginmanager.getplugin('xdist')):
        config.pluginmanager.register(SplinterXdistPlugin())


class NodesAction(argparse.Action):

    """Parses out a space-separated list of nodes and extends dest with it."""

    def __call__(self, parser, namespace, values, option_string=None):
        items = argparse._copy.copy(argparse._ensure_value(namespace, self.dest, []))
        items.extend([value.strip() for value in values.split()])
        setattr(namespace, self.dest, items)


def get_virtualenv_path():
    """Get virtualenv path if test process is using virtual environment inside of current folder."""
    venv_path = os.path.realpath(os.path.dirname(os.path.dirname(sys.executable)))
    if os.path.realpath(os.environ['PWD']) in venv_path:
        return os.path.relpath(venv_path)


def pytest_addoption(parser):
    """Pytest hook to add custom command line option(s)."""
    group = parser.getgroup("cloud", "distributed tests scheduler")
    group.addoption(
        "--cloud-python",
        help="python executable name to be used on the remote test nodes."
        "Default is the executable used on the master.", type='string', action="store",
        dest='cloud_python', metavar="NAME", default='python{0}.{1}'.format(*sys.version_info))
    group._addoption(
        '--cloud-chdir',
        metavar='DIR',
        action="store", dest="cloud_chdir",
        default=os.path.join(
            'pytest',
            os.environ['USER'],
            os.path.basename(os.environ['PWD'])
        ).replace(os.path.sep, '_'),
        help="relative path on remote node to run tests in. Default is pytest_<username>_<current_folder_name>")
    group.addoption(
        "--cloud-nodes",
        help="space-separated test node list to use for distributed testing", type='string', action=NodesAction,
        dest='cloud_nodes', metavar="'USER@HOST", default=[])
    group.addoption(
        "--cloud-node",
        help="test node to use for distributed testing", type='string', action="append",
        dest='cloud_nodes', metavar="USER@HOST", default=[])
    group.addoption(
        "--cloud-virtualenv-path",
        help="relative path to the virtualenv to be used on the remote test nodes.", type='string', action="store",
        dest='cloud_virtualenv_path', metavar="PATH", default=get_virtualenv_path())
    group.addoption(
        "--cloud-skip-virtualenv-rsync",
        help="Skip an rsync of the virtualenv folder.", action="store_true",
        dest='cloud_skip_virtualenv_rsync', default=False)
    group.addoption(
        "--cloud-mem-per-process",
        help="amount of memory roughly needed for test process, in megabytes", type='int', action="store",
        dest='cloud_mem_per_process', metavar="NUMBER", default=None)
    group.addoption(
        "--cloud-max-processes",
        help="maximum number of processes per test node", type='int', action="store",
        dest='cloud_max_processes', metavar="NUMBER", default=None)


@pytest.mark.tryfirst
def pytest_cmdline_main(config):
    """Custom cmd line manipulation for pytest-cloud."""
    check_options(config)


def activate_env(channel, virtualenv_path):
    """Activate virtual environment.

    Executed on the remote side.

    :param channel: execnet channel for communication with master node
    :type channel: execnet.gateway_base.Channel
    :param virtualenv_path: relative path to the virtualenv to activate on the remote test node
    :type virtualenv_path: str
    """
    import os.path
    import sys
    import subprocess
    PY3 = sys.version_info[0] > 2
    subprocess.check_call(['find', '.', '-name', '*.pyc', '-delete'])
    subprocess.check_call(['find', '.', '-name', '__pycache__', '-delete'])
    if virtualenv_path:
        activate_script = os.path.abspath(os.path.normpath(os.path.join(virtualenv_path, 'bin', 'activate_this.py')))
        if PY3:
            exec(compile(open(activate_script).read()))
        else:
            execfile(activate_script, {'__file__': activate_script})  # NOQA


def get_node_capabilities(channel):
    """Get test node capabilities.

    Executed on the remote side.

    :param channel: execnet channel for communication with master node
    :type channel: execnet.gateway_base.Channel

    :return: `dict` in form {'cpu_count': 1, 'virtual_memory': {'available': 100, 'total': 200}}
    :rtype: dict
    """
    import psutil
    memory = psutil.virtual_memory()
    caps = dict(cpu_count=psutil.cpu_count(), virtual_memory=dict(available=memory.available, total=memory.total))
    channel.send(caps)


def get_node_specs(node, host, caps, python=None, chdir=None, mem_per_process=None, max_processes=None):
    """Get single node specs.

    Executed on the master node side.

    :param node: node name in form <username>@<hostname>
    :type node: str
    :param host: hostname of the node
    :type host: str
    :param python: python executable name to use on the remote side
    :type python: str
    :param chdir: relative path where to run (and sync) tests on the remote side
    :type chdir: str
    :param mem_per_process: optional amount of memory per process needed, in megabytest
    :type mem_per_process: int
    :param max_processes: optional maximum number of processes per test node
    :type max_processes: int

    :return: `list` of test gateway specs for single test node in form ['1*ssh=<node>//id=<hostname>_<index>', ...]
    :rtype: list
    """
    count = min(max_processes or six.MAXSIZE, caps['cpu_count'])
    if mem_per_process:
        count = min(int(math.floor(caps['virtual_memory']['available'] / mem_per_process)), count)
    for index in range(count):
        if index == 0:
            fmt = 'ssh={node}//id={host}_{index}//chdir={chdir}//python={python}'
        else:
            fmt = 'popen//id={host}_{index}//chdir={chdir}//python={python}'
        yield fmt.format(
            count=count,
            node=node,
            host=host,
            index=index,
            chdir=chdir,
            python=python)


def unique_everseen(iterable, key=None):
    """List unique elements, preserving order. Remember all elements ever seen."""
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


@timeout_decorator.timeout(3)
def make_gateway(group, spec):
    """Make a gateway."""
    group.makegateway(spec)


def get_nodes_specs(
        nodes, python=None, chdir=None, virtualenv_path=None, mem_per_process=None,
        max_processes=None, config=None):
    """Get nodes specs.

    Get list of node names, connect to each of them, get the system information, produce the list of node specs out of
    that information filtering non-connectable nodes and nodes which don't comply the requirements.
    Executed on the master node side.

    :param nodes: `list` of node names in form [[<username>@]<hostname>, ...]
    :type nodes: list
    :param python: python executable name to use on the remote side
    :type python: str
    :param chdir: relative path where to run (and sync) tests on the remote side
    :type chdir: str
    :param virtualenv_path: relative path to the virtualenv to activate on the remote test node
    :type virtualenv_path: str
    :param mem_per_process: optional amount of memory per process needed, in megabytest
    :type mem_per_process: int
    :param max_processes: optional maximum number of processes per test node
    :type max_processes: int
    :param config: pytest config object
    :type config: pytest.Config

    :return: `list` of test gateway specs for all test nodes which confirm given requirements
        in form ['1*ssh=<node>//id=<hostname>:<index>', ...]
    :rtype: list
    """
    group = execnet.Group()
    try:
        if virtualenv_path:
            nm = NodeManager(config, specs=[])
            virtualenv_path = os.path.relpath(virtualenv_path)
        node_specs = []
        node_caps = {}
        root_dir = getrootdir(config, '')
        print('Detected root dir: {0}'.format(root_dir))
        rsync = RSync(root_dir, chdir, includes=config.getini("rsyncdirs"), **nm.rsyncoptions)
        print('Detecting connectable test nodes...')
        for node in unique_everseen(nodes):
            host = node.split('@')[1] if '@' in node else node
            spec = 'ssh={node}//id={host}//chdir={chdir}//python={python}'.format(
                node=node,
                host=host,
                chdir=chdir,
                python=python)
            try:
                make_gateway(group, spec)
            except Exception:
                continue
            rsync.add_target_host(node)
            node_specs.append((node, host))
        if node_specs:
            print('Found {0} connectable test nodes: {1}'.format(len(node_specs), rsync.targets))
        else:
            pytest.exit('None of the given test nodes are connectable')
        print('RSyncing directory structure')
        rsync.send()
        print('RSync finished')
        group.remote_exec(activate_env, virtualenv_path=virtualenv_path).waitclose()
        multi_channel = group.remote_exec(get_node_capabilities)
        try:
            caps = multi_channel.receive_each(True)
            for ch, cap in caps:
                node_caps[ch.gateway.id] = cap
        finally:
            multi_channel.waitclose()
        return list(chain.from_iterable(
            get_node_specs(
                node, hst, node_caps[hst], python=python, chdir=chdir, mem_per_process=mem_per_process,
                max_processes=max_processes)
            for node, hst in node_specs)
        )
    finally:
        try:
            group.terminate()
        except Exception:
            pass


def check_options(config):
    """Process options to manipulate (produce other options) important for pytest-cloud."""
    if getattr(config, 'slaveinput', {}).get('slaveid', 'local') == 'local' and config.option.cloud_nodes:
        patches.apply()
        mem_per_process = config.option.cloud_mem_per_process
        if mem_per_process:
            mem_per_process = mem_per_process * 1024 * 1024
        virtualenv_path = config.option.cloud_virtualenv_path
        chdir = config.option.cloud_chdir
        python = config.option.cloud_python
        node_specs = get_nodes_specs(
            config.option.cloud_nodes,
            chdir=chdir,
            python=python,
            virtualenv_path=virtualenv_path,
            max_processes=config.option.cloud_max_processes,
            mem_per_process=mem_per_process,
            config=config)
        if node_specs:
            print('Scheduling with {0} parallel test sessions'.format(len(node_specs)))
        if not node_specs:
            pytest.exit('None of the given test nodes are able to serve as a test node due to capabilities')
        config.option.tx += node_specs
        config.option.dist = 'load'
