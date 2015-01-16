"""Distributed tests planner plugin for pytest testing framework.

Provides an easy way of running tests amoung several test nodes (slaves).
"""


class SplinterXdistPlugin(object):

    """Plugin class to defer pytest-xdist hook handler."""


def pytest_configure(config):
    """Register pytest-cloud's deferred plugin."""
    if config.pluginmanager.getplugin('xdist'):
        config.pluginmanager.register(SplinterXdistPlugin())


def pytest_addoption(parser):  # pragma: no cover
    """Pytest hook to add custom command line option(s)."""
    group = parser.getgroup("cloud", "distributed tests scheduler")
    group.addoption(
        "--cloud-node",
        help="pytest-cloud webdriver", type='string', action="append",
        dest='cloud_nodes', metavar="HOST", default=[])


def pytest_cmdline_main(config):
    """Custom cmd line manipulation for pytest-cloud."""
    check_options(config)


def check_options(config):
    """Process options to manipulate (produce other options) important for pytest-cloud."""
    if config.option.cloud_nodes:
        config.option.tx += [
            'ssh={node}//id={host}'.format(node=node, host=node.split('@')[1] if '@' in node else node)
            for node in config.option.cloud_nodes]
        config.option.dist = 'load'
