# Copyright 2009-2012 Yelp
# Copyright 2013 Lyft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test compatibility switching between different Hadoop versions"""

import os
from distutils.version import LooseVersion

from mrjob.compat import jobconf_from_env
from mrjob.compat import jobconf_from_dict
from mrjob.compat import supports_combiners_in_hadoop_streaming
from mrjob.compat import supports_new_distributed_cache_options
from mrjob.compat import translate_jobconf
from mrjob.compat import uses_generic_jobconf
from mrjob.compat import _map_version

from tests.py2 import TestCase
from tests.py2 import patch


class GetJobConfValueTestCase(TestCase):

    def setUp(self):
        p = patch.object(os, 'environ', {})
        p.start()
        self.addCleanup(p.stop)

    def test_get_old_hadoop_jobconf(self):
        os.environ['user_name'] = 'Edsger W. Dijkstra'
        self.assertEqual(jobconf_from_env('user.name'),
                         'Edsger W. Dijkstra')
        self.assertEqual(jobconf_from_env('mapreduce.job.user.name'),
                         'Edsger W. Dijkstra')

    def test_get_new_hadoop_jobconf(self):
        os.environ['mapreduce_job_user_name'] = 'Edsger W. Dijkstra'
        self.assertEqual(jobconf_from_env('user.name'),
                         'Edsger W. Dijkstra')
        self.assertEqual(jobconf_from_env('mapreduce.job.user.name'),
                         'Edsger W. Dijkstra')

    def test_default(self):
        self.assertEqual(jobconf_from_env('user.name'), None)
        self.assertEqual(jobconf_from_env('user.name', 'dave'), 'dave')

    def test_get_missing_jobconf_not_in_table(self):
        # there was a bug where defaults didn't work for jobconf
        # variables that we don't know about
        self.assertEqual(jobconf_from_env('user.defined'), None)
        self.assertEqual(jobconf_from_env('user.defined', 'beauty'), 'beauty')


class JobConfFromDictTestCase(TestCase):

    def test_get_old_hadoop_jobconf(self):
        jobconf = {'user.name': 'Edsger W. Dijkstra'}
        self.assertEqual(jobconf_from_dict(jobconf, 'user.name'),
                         'Edsger W. Dijkstra')
        self.assertEqual(jobconf_from_dict(jobconf, 'mapreduce.job.user.name'),
                         'Edsger W. Dijkstra')

    def test_get_new_hadoop_jobconf(self):
        jobconf = {'mapreduce.job.user.name': 'Edsger W. Dijkstra'}
        self.assertEqual(jobconf_from_dict(jobconf, 'user.name'),
                         'Edsger W. Dijkstra')
        self.assertEqual(jobconf_from_dict(jobconf, 'mapreduce.job.user.name'),
                         'Edsger W. Dijkstra')

    def test_default(self):
        self.assertEqual(jobconf_from_dict({}, 'user.name'), None)
        self.assertEqual(jobconf_from_dict({}, 'user.name', 'dave'), 'dave')

    def test_get_missing_jobconf_not_in_table(self):
        # there was a bug where defaults didn't work for jobconf
        # variables that we don't know about
        self.assertEqual(jobconf_from_dict({}, 'user.defined'), None)
        self.assertEqual(
            jobconf_from_dict({}, 'user.defined', 'beauty'), 'beauty')


class CompatTestCase(TestCase):

    def test_translate_jobconf(self):
        self.assertEqual(translate_jobconf('user.name', '0.18'),
                         'user.name')
        self.assertEqual(translate_jobconf('mapreduce.job.user.name', '0.18'),
                         'user.name')
        self.assertEqual(translate_jobconf('user.name', '0.19'),
                         'user.name')
        self.assertEqual(
            translate_jobconf('mapreduce.job.user.name', '0.19.2'),
            'user.name')
        self.assertEqual(translate_jobconf('user.name', '0.21'),
                         'mapreduce.job.user.name')

        self.assertEqual(translate_jobconf('user.name', '1.0'),
                         'user.name')
        self.assertEqual(translate_jobconf('user.name', '2.0'),
                         'mapreduce.job.user.name')

    def test_supports_combiners(self):
        self.assertEqual(supports_combiners_in_hadoop_streaming('0.19'),
                         False)
        self.assertEqual(supports_combiners_in_hadoop_streaming('0.19.2'),
                         False)
        self.assertEqual(supports_combiners_in_hadoop_streaming('0.20'),
                         True)
        self.assertEqual(supports_combiners_in_hadoop_streaming('0.20.203'),
                         True)

    def test_uses_generic_jobconf(self):
        self.assertEqual(uses_generic_jobconf('0.18'), False)
        self.assertEqual(uses_generic_jobconf('0.20'), True)
        self.assertEqual(uses_generic_jobconf('0.21'), True)

    def test_cache_opts(self):
        self.assertEqual(supports_new_distributed_cache_options('0.18'), False)
        self.assertEqual(supports_new_distributed_cache_options('0.20'), False)
        self.assertEqual(
            supports_new_distributed_cache_options('0.20.203'), True)


class MapVersionTestCase(TestCase):

    def test_empty(self):
        self.assertRaises(ValueError, _map_version, None, '0.5.0')
        self.assertRaises(ValueError, _map_version, {}, '0.5.0'),
        self.assertRaises(ValueError, _map_version, [], '0.5.0')

    def test_dict(self):
        version_map = {
            '1': 'foo',
            '2': 'bar',
            '3': 'baz',
        }

        self.assertEqual(_map_version(version_map, '1.1'), 'foo')
        # test exact match
        self.assertEqual(_map_version(version_map, '2'), 'bar')
        # versions are just minimums
        self.assertEqual(_map_version(version_map, '4.5'), 'baz')
        # compare versions, not strings
        self.assertEqual(_map_version(version_map, '11.11'), 'baz')
        # fall back to lowest version
        self.assertEqual(_map_version(version_map, '0.1'), 'foo')

    def test_list_of_tuples(self):
        version_map = [
            (LooseVersion('1'), 'foo'),
            (LooseVersion('2'), 'bar'),
            (LooseVersion('3'), 'baz'),
        ]

        self.assertEqual(_map_version(version_map, '1.1'), 'foo')
        self.assertEqual(_map_version(version_map, '2'), 'bar')
        self.assertEqual(_map_version(version_map, '4.5'), 'baz')
        self.assertEqual(_map_version(version_map, '11.11'), 'baz')
        self.assertEqual(_map_version(version_map, '0.1'), 'foo')
