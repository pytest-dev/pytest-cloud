"""Distributed tests planner plugin for pytest testing framework.

Provides an easy way of running tests amoung several test nodes (slaves).
"""
from __future__ import division
import argparse
import itertools
import math
import os.path
import sys

import py
import execnet
from xdist.slavemanage import (
    HostRSync,
    NodeManager,
)
import six

import pytest


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
        getattr(config, 'slaveinput', {}).get('slaveid', 'local') == 'local'
            and config.option.cloud_nodes
            and config.pluginmanager.getplugin('xdist')):
        config.pluginmanager.register(SplinterXdistPlugin())


class NodesAction(argparse.Action):

    """Parses out a space-separated list of nodes and extends dest with it."""

    def __call__(self, parser, namespace, values, option_string=None):
        items = argparse._copy.copy(argparse._ensure_value(namespace, self.dest, []))
        items.extend([value.strip() for value in values.split()])
        setattr(namespace, self.dest, items)


def get_virtualenv_path():
    """Get virtualenv path if test process is using virtual environment inside of current folder."""
    venv_path = os.path.dirname(os.path.dirname(sys.executable))
    if os.environ['PWD'] in venv_path:
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
        "--cloud-mem-per-process",
        help="amount of memory roughly needed for test process, in megabytes", type='int', action="store",
        dest='cloud_mem_per_process', metavar="NUMBER", default=None)
    group.addoption(
        "--cloud-max-processes",
        help="maximum number of processes per test node", type='int', action="store",
        dest='cloud_max_processes', metavar="NUMBER", default=None)


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
    PY3 = sys.version_info[0] > 2

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

    :return: `dict` in form {'cpu_count': 1, 'virtual_memory': {'free': 100, 'total': 200}}
    :rtype: dict
    """
    import psutil
    memory = psutil.virtual_memory()
    caps = dict(cpu_count=psutil.cpu_count(), virtual_memory=dict(free=memory.free, total=memory.total))
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
        count = min(int(math.floor(caps['virtual_memory']['free'] / mem_per_process)), count)
    return (
        '1*ssh={node}//id={host}_{index}//chdir={chdir}//python={python}'.format(
            count=count,
            node=node,
            host=host,
            index=index,
            chdir=chdir,
            python=python)
        for index in range(count))


def get_nodes_specs(
        nodes, python=None, chdir=None, virtualenv_path=None, mem_per_process=None, max_processes=None,
        config=None):
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
    if virtualenv_path:
        nm = NodeManager(config, specs=[])
        rsync_virtualenv_path = py.path.local(virtualenv_path).realpath()
        virtualenv_path = os.path.relpath(virtualenv_path)
    node_specs = []
    node_caps = {}
    for node in nodes:
        host = node.split('@')[1] if '@' in node else node
        spec = 'ssh={node}//id={host}//chdir={chdir}//python={python}'.format(
            node=node,
            host=host,
            chdir=chdir,
            python=python)
        try:
            gw = group.makegateway(spec)
        except Exception:
            continue
        if virtualenv_path:
            rsync = HostRSync(rsync_virtualenv_path, **nm.rsyncoptions)
            rsync.add_target_host(gw)
            rsync.send()
        node_specs.append((node, host))
    if not node_specs:
        pytest.exit('None of the given test nodes are connectable')
    try:
        group.remote_exec(activate_env, virtualenv_path=virtualenv_path).waitclose()
        multi_channel = group.remote_exec(get_node_capabilities)
        try:
            caps = multi_channel.receive_each(True)
            for ch, cap in caps:
                node_caps[ch.gateway.id] = cap
        finally:
            multi_channel.waitclose()
        return list(itertools.chain.from_iterable(
            get_node_specs(
                node, hst, node_caps[hst], python=python, chdir=chdir, mem_per_process=mem_per_process,
                max_processes=max_processes)
            for node, hst in node_specs)
        )
    finally:
        group.terminate()


def check_options(config):
    """Process options to manipulate (produce other options) important for pytest-cloud."""
    if getattr(config, 'slaveinput', {}).get('slaveid', 'local') == 'local' and config.option.cloud_nodes:
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
        if virtualenv_path:
            ini_rsync_dirs = config.getini("rsyncdirs")
            if virtualenv_path in config.option.rsyncdir:
                config.option.rsyncdir.remove(virtualenv_path)
            if virtualenv_path in ini_rsync_dirs:
                ini_rsync_dirs.remove(virtualenv_path)
        config.option.tx += node_specs
        config.option.dist = 'load'
