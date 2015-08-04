"""Monkey patches."""
import os
import xdist
from xdist import slavemanage

from .rsync import make_reltoroot


def rsync(self, gateway, source, notify=None, verbose=False, ignores=None):
    """Perform rsync to remote hosts for node."""
    spec = gateway.spec
    if spec.popen and not spec.chdir:
        gateway.remote_exec("""
            import sys ; sys.path.insert(0, %r)
        """ % os.path.dirname(str(source))).waitclose()
        return
    if (spec, source) in self._rsynced_specs:
        return

    self.config.hook.pytest_xdist_rsyncstart(
        source=source,
        gateways=[gateway],
    )
    self.config.hook.pytest_xdist_rsyncfinish(
        source=source,
        gateways=[gateway],
    )


def activate_env(channel, virtualenv_path, develop_eggs=None):
    """Activate virtual environment.

    Executed on the remote side.

    :param channel: execnet channel for communication with master node
    :type channel: execnet.gateway_base.Channel
    :param virtualenv_path: relative path to the virtualenv to activate on the remote test node
    :type virtualenv_path: str
    :param develop_eggs: optional list of python packages to be installed in develop mode
    :type develop_eggs: list
    """
    import os.path  # pylint: disable=W0404
    import sys  # pylint: disable=W0404
    import subprocess  # pylint: disable=W0404
    from itertools import chain  # pylint: disable=W0404
    PY3 = sys.version_info[0] > 2
    subprocess.check_call(['find', '.', '-name', '*.pyc', '-delete'])
    if virtualenv_path:
        if develop_eggs:
            python_script = os.path.abspath(os.path.normpath(os.path.join(virtualenv_path, 'bin', 'python')))
            pip_script = os.path.abspath(os.path.normpath(os.path.join(virtualenv_path, 'bin', 'pip')))
            args = (
                (python_script, pip_script, 'install', '--no-index', '--no-deps') +
                tuple(chain.from_iterable([('-e', egg) for egg in develop_eggs])))
            subprocess.check_call(args)
        activate_script = os.path.abspath(os.path.normpath(os.path.join(virtualenv_path, 'bin', 'activate_this.py')))
        if PY3:
            exec(compile(open(activate_script).read()))  # pylint: disable=W0122
        else:
            execfile(activate_script, {'__file__': activate_script})  # NOQA


def setup(self):
    """Setup a new test slave."""
    self.log("setting up slave session")
    spec = self.gateway.spec
    args = self.config.args
    if not spec.popen or spec.chdir:
        args = make_reltoroot(self.nodemanager.roots, args)
    option_dict = vars(self.config.option)
    if spec.popen and not spec.via:
        name = "popen-%s" % self.gateway.id
        basetemp = self.config._tmpdirhandler.getbasetemp()
        option_dict['basetemp'] = str(basetemp.join(name))
    self.config.hook.pytest_configure_node(node=self)
    self.channel = self.gateway.remote_exec(xdist.remote)
    if self.putevent:
        self.channel.setcallback(
            self.process_from_remote,
            endmarker=self.ENDMARK)
    self.channel.send((self.slaveinput, args, option_dict))


def apply_patches():
    """Apply monkey patches."""
    slavemanage.make_reltoroot = make_reltoroot
    slavemanage.NodeManager.rsync = rsync
    slavemanage.SlaveController.setup = setup
