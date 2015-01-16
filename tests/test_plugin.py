"""Tests for pytest-bdd-splinter subplugin."""
import mock


@mock.patch('xdist.dsession.DSession')
def test_schedule(mocked_dsession, testdir, monkeypatch):
    """Test scheduling of tests on given nodes."""
    testdir.inline_run('--cloud-node=10.0.10.1', '--cloud-node=10.0.10.2')
    config = mocked_dsession.call_args[0][0]
    assert config.option.tx == ['ssh=10.0.10.1//id=10.0.10.1', 'ssh=10.0.10.2//id=10.0.10.2']
    assert config.option.dist == 'load'

    testdir.inline_run('--cloud-node=user@10.0.10.1', '--cloud-node=user2@10.0.10.2')
    config = mocked_dsession.call_args[0][0]
    assert config.option.tx == ['ssh=user@10.0.10.1//id=10.0.10.1', 'ssh=user2@10.0.10.2//id=10.0.10.2']
    assert config.option.dist == 'load'
