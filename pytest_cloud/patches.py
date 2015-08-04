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
    self.channel.send((self.slaveinput, args, option_dict))
    if self.putevent:
        self.channel.setcallback(
            self.process_from_remote,
            endmarker=self.ENDMARK)


def apply_patches():
    """Apply monkey patches."""
    slavemanage.make_reltoroot = make_reltoroot
    slavemanage.NodeManager.rsync = rsync
    slavemanage.SlaveController.setup = setup
