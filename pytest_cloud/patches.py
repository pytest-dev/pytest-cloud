"""Monkey patches."""
import os
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


def apply_patches():
    """Apply monkey patches."""
    slavemanage.make_reltoroot = make_reltoroot
    slavemanage.NodeManager.rsync = rsync
