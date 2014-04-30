#!/usr/bin/python
# coding=utf-8
################################################################################
import os
from test import CollectorTestCase
from test import get_collector_config
from test import unittest
from mock import Mock
from mock import patch

try:
    from cStringIO import StringIO
    StringIO  # workaround for pyflakes issue #13
except ImportError:
    from StringIO import StringIO

from diamond.collector import Collector
from memory_docker import MemoryDockerCollector
import docker

dirname = os.path.dirname(__file__)
fixtures_path = os.path.join(dirname, 'fixtures/')
fixtures = []
for root, dirnames, filenames in os.walk(fixtures_path):
    fixtures.append([root, dirnames, filenames])

docker_fixture = [
    {u'Id': u'c3341726a9b4235a35b390c5f6f28e5a6869879a48da1d609db8f6bf4275bdc5',
     u'Names': [u'/testcontainer']},
    {u'Id': u'9c151939e20682b924d7299875e94a4aabbe946b30b407f89e276507432c625b',
     u'Names': None}]


class TestMemoryDockerCollector(CollectorTestCase):
    def setUp(self):
        config = get_collector_config('MemoryDockerCollector', {
            'interval': 10,
            'byte_unit': 'megabyte'
        })

        self.collector = MemoryDockerCollector(config, None)

    def test_import(self):
        self.assertTrue(MemoryDockerCollector)

    @patch('__builtin__.open')
    @patch('os.walk', Mock(return_value=iter(fixtures)))
    @patch.object(docker.Client, 'containers', Mock(return_value=[]))
    @patch.object(Collector, 'publish')
    def test_should_open_all_cpuacct_stat(self, publish_mock, open_mock):
        open_mock.side_effect = lambda x: StringIO('')
        self.collector.collect()
        open_mock.assert_any_call(
            fixtures_path + 'lxc/testcontainer/memory.stat')
        open_mock.assert_any_call(fixtures_path + 'lxc/memory.stat')
        open_mock.assert_any_call(fixtures_path + 'memory.stat')

    @patch('__builtin__.open')
    @patch('os.walk', Mock(return_value=iter(fixtures)))
    @patch.object(docker.Client, 'containers')
    @patch.object(Collector, 'publish')
    def test_should_get_containers(self, publish_mock, containers_mock,
                                   open_mock):
        containers_mock.return_value = []
        open_mock.side_effect = lambda x: StringIO('')
        self.collector.collect()
        containers_mock.assert_any_call(all=True)

    @patch.object(Collector, 'publish')
    @patch.object(docker.Client, 'containers',
                  Mock(return_value=docker_fixture))
    def test_should_work_with_real_data(self, publish_mock):
        MemoryDockerCollector.MEMORY_PATH = fixtures_path
        self.collector.collect()

        self.assertPublishedMany(publish_mock, {
            'lxc.testcontainer.cache': 1,
            'lxc.testcontainer.rss': 1,
            'lxc.testcontainer.swap': 1,
            'lxc.cache': 1,
            'lxc.rss': 1,
            'lxc.swap': 1,
            'system.cache': 1,
            'system.rss': 1,
            'system.swap': 1,
            'docker.testcontainer.cache': 1,
            'docker.testcontainer.rss': 1,
            'docker.testcontainer.swap': 1,
            'docker.cache': 1,
            'docker.rss': 1,
            'docker.swap': 1,
        })

if __name__ == "__main__":
    unittest.main()