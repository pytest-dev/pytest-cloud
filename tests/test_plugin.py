"""Tests for pytest-bdd-splinter subplugin."""
import sys

import mock
import pytest

import xdist.dsession
import execnet
import pytest_cloud.plugin


PYTHON = 'python{0}.{1}'.format(*sys.version_info)


@pytest.fixture
def mocked_group(request):
    """Mock execnet.Group."""
    group = execnet.Group

    def fin():
        execnet.Group = group

    mocked_group = mock.Mock()
    request.addfinalizer(fin)
    mocked_group.mkgateway.return_value = mock.Mock()
    execnet.Group = mocked_group
    return mocked_group


@pytest.fixture
def mocked_dsession(request):
    """Mock xdist.dsession.DSession."""
    dsession = xdist.dsession.DSession

    def fin():
        xdist.dsession.DSession = dsession

    mocked_dsession = mock.Mock()
    request.addfinalizer(fin)

    def iterate():
        yield
        yield

    def dic():
        return {}

    def rep():
        class Report(object):
            skipped = []
            call = []
            failed = []
            result = []
            passed = True
            outcome = 'OK'
            nodeid = 123
        return Report()

    mocked_dsession.return_value.pytest_addhooks = iterate
    mocked_dsession.return_value.pytest_namespace = dic
    mocked_dsession.return_value.pytest_addoption = iterate
    mocked_dsession.return_value.pytest_configure = iterate
    mocked_dsession.return_value.pytest_collectstart = iterate
    mocked_dsession.return_value.pytest_make_collect_report = rep
    mocked_dsession.return_value.pytest_collectreport = iterate
    mocked_dsession.return_value.pytest_collection_modifyitems = iterate

    xdist.dsession.DSession = mocked_dsession
    return mocked_dsession


@pytest.fixture
def mocked_rsync(request):
    """Mock pytest_cloud.plugin.RSync."""
    rsync = pytest_cloud.plugin.RSync

    def fin():
        pytest_cloud.plugin.RSync = rsync

    request.addfinalizer(fin)

    mocked_rsync = mock.Mock()
    pytest_cloud.plugin.RSync = mocked_rsync

    return mocked_rsync


@pytest.mark.parametrize(
    ['host1', 'user1', 'cpu_count1', 'memory1', 'host2', 'user2', 'cpu_count2', 'memory2',
     'mem_per_process', 'max_processes', 'result'],
    [
        ('1.example.com', '', 2, 100,
         '2.example.com', 'user', 1, 200,
         None,
         None,
         [
             'ssh=1.example.com//id=1.example.com_0//chdir=test//python=',
             'ssh=1.example.com//id=1.example.com_1//chdir=test//python=',
             'ssh=user@2.example.com//id=2.example.com_0//chdir=test//python=',
         ]),
        ('1.example.com', '', 2, 100,
         '2.example.com', 'user', 1, 200,
         200,
         None,
         [
             'ssh=user@2.example.com//id=2.example.com_0//chdir=test//python=',
         ]),
        ('1.example.com', '', 2, 100,
         '2.example.com', 'user', 1, 200,
         None,
         1,
         [
             'ssh=1.example.com//id=1.example.com_0//chdir=test//python=',
             'ssh=user@2.example.com//id=2.example.com_0//chdir=test//python=',
         ]),
        ('1.example.com', '', 2, 100,
         '2.example.com', 'user', 1, 200,
         200,
         1,
         [
             'ssh=user@2.example.com//id=2.example.com_0//chdir=test//python=',
         ]),
        ('1.example.com', '', 2, 100,
         '2.example.com', 'user', 1, 200,
         200,
         1,
         [
             'ssh=user@2.example.com//id=2.example.com_0//chdir=test//python=',
         ]),
    ]
)
def test_schedule(
        mocked_dsession, mocked_group, mocked_rsync, testdir, host1, host2, user1, user2, cpu_count1,
        cpu_count2, memory1, memory2, mem_per_process, max_processes, result, request):
    """Test scheduling of tests on given nodes."""
    ch1 = mock.Mock()
    ch1.gateway.id = host1
    ch2 = mock.Mock()
    ch2.gateway.id = host2

    node1 = user1 + '@' + host1 if user1 else host1
    node2 = user2 + '@' + host2 if user2 else host2

    mocked_group.return_value.remote_exec.return_value.receive_each.return_value = [
        (ch1, {'cpu_count': cpu_count1, 'virtual_memory': {'available': memory1 * 1024 ** 2}}),
        (ch2, {'cpu_count': cpu_count2, 'virtual_memory': {'available': memory2 * 1024 ** 2}}),
    ]
    params = [
        '--cloud-nodes={0}'.format(node1),
        '--cloud-node={0}'.format(node2),
        '--cloud-chdir=test',
    ]
    if mem_per_process:
        params.append('--cloud-mem-per-process={0}'.format(mem_per_process))
    if max_processes:
        params.append('--cloud-max-processes={0}'.format(max_processes))
    testdir.inline_run(*params)
    assert mocked_rsync.call_args[0] == (testdir.tmpdir, 'test')
    assert mocked_rsync.return_value.add_target_host.call_args_list == [
        mock.call(node1,),
        mock.call(node2,)]
    assert mocked_rsync.return_value.send.called
    config = mocked_dsession.call_args[0][0]
    assert all(tx.startswith(expected) for tx, expected in zip(config.option.tx, result))
    assert config.option.dist == 'load'
