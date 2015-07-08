"""Monkey patches."""
import os
import py
from xdist import slavemanage

from .rsync import make_reltoroot


def rsync(self, gateway, source, notify=None, verbose=False, ignores=None):
    """Perform rsync to remote hosts for node."""
    spec = gateway.spec
    if spec.popen and not spec.chdir:
        # XXX This assumes that sources are python-packages
        #     and that adding the basedir does not hurt.
        gateway.remote_exec("""
            import sys ; sys.path.insert(0, %r)
        """ % os.path.dirname(str(source))).waitclose()
        return
    if (spec, source) in self._rsynced_specs:
        return

    def finished():
        if notify:
            notify("rsyncrootready", spec, source)
    self.config.hook.pytest_xdist_rsyncstart(
        source=source,
        gateways=[gateway],
    )
    self.config.hook.pytest_xdist_rsyncfinish(
        source=source,
        gateways=[gateway],
    )


def apply():
    """Apply monkey patches."""
    slavemanage.make_reltoroot = make_reltoroot
    slavemanage.NodeManager.rsync = rsync
