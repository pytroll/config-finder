#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016.

# Author(s):

#   Martin Raspaud <martin.raspaud@smhi.se>
#   Adam Dybbroe <adam.dybbroe@smhi.se>
#   David Hoese <david.hoese@ssec.wisc.edu>

# This file is part of the satpy.

# satpy is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# satpy is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with satpy.  If not, see <http://www.gnu.org/licenses/>.

"""Configuration directory and file handling
"""

import logging
import os
import unittest
from collections import Mapping

import yaml

from six.moves import configparser

LOG = logging.getLogger(__name__)

__version__ = 'v0.1.1'


def recursive_dict_update(d, u):
    """Recursive dictionary update.

    Copied from:

        http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth

    """
    for k, v in u.items():
        if isinstance(v, Mapping):
            r = recursive_dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def config_search_paths(filename, *search_dirs, **kwargs):
    """Get the config path in search_dirs."""
    paths = []
    paths += [os.path.join(search_dir, filename)
              for search_dir in search_dirs
              if search_dir is not None]

    if kwargs.get("check_exists", True):
        paths = [x for x in paths if os.path.isfile(x)]

    return paths


class MyParser(configparser.ConfigParser):
    """PFE.

    http://stackoverflow.com/questions/3220670/read-all-the-contents-in-ini-file-into-dictionary-with-python
    """

    def as_dict(self):
        """Return config file content as a dictionary."""
        d__ = dict(self._sections)
        for key in d__:
            d__[key] = dict(self._defaults, **d__[key])
            d__[key].pop('__name__', None)
        return d__


class ConfigFinder(object):
    """Helper to find config files and load them in a layered manner."""

    def __init__(self, *paths):
        """*paths* to find the config files in.

        Config files in first paths get overriden by the config files in the
        later paths.
        """
        self.paths = paths

    def __call__(self, filename):
        """Find and merge configs."""
        config_files = config_search_paths(
            filename, *self.paths, check_exists=True)
        ext = os.path.splitext(filename)[1]
        if ext in ['.cfg', '.ini']:
            cfg = MyParser()
            for config_file in config_files:
                cfg.read(config_file)
            return cfg.as_dict()

        elif ext in ['.yaml', '.yml']:
            cfg = {}
            for config_file in config_files:
                with open(config_file) as fd_:
                    cfg = recursive_dict_update(cfg, yaml.load(fd_))
            return cfg


class TestRecursiveDictUpdate(unittest.TestCase):
    """Test the recursive dict updating."""

    def test_recursive_dict_update(self):

        dict1 = {'a': 1, 'b': {'c': 3, 'd': 4}}

        dict2 = {'a': 2, 'b': {'d': 5}}

        self.assertDictEqual(recursive_dict_update(dict1, dict2),
                             {'a': 2,
                              'b': {'c': 3, 'd': 5}})


class TestConfigSearch(unittest.TestCase):
    """Test the config file search."""

    def test_config_search_path(self):
        """Test the config_search_path function."""
        self.assertEqual(config_search_paths('conf.cfg', '/tmp', '.', check_exists=False),
                         ['/tmp/conf.cfg', './conf.cfg'])

        self.assertEqual(config_search_paths('conf.cfg', '/tmp', '.'), [])
        with open('/tmp/conf.cfg', 'w') as fd_:
            pass

        with open('./conf.cfg', 'w') as fd_:
            pass

        self.assertEqual(config_search_paths('conf.cfg', '/tmp', '.'),
                         ['/tmp/conf.cfg', './conf.cfg'])

        os.remove('/tmp/conf.cfg')
        os.remove('./conf.cfg')


class TestConfigFinder(unittest.TestCase):
    """Test config_finder."""

    def test_yaml(self):
        """Test yaml merging."""
        config_finder = ConfigFinder('/tmp', '.')

        dict1 = {'a': 1, 'b': {'c': 3, 'd': 4}}

        dict2 = {'a': 2, 'b': {'d': 5}}

        with open('/tmp/conf.yaml', 'w') as fd_:
            yaml.dump(dict1, fd_)

        with open('./conf.yaml', 'w') as fd_:
            yaml.dump(dict2, fd_)

        self.assertDictEqual(config_finder('conf.yaml'),
                             {'a': 2,
                              'b': {'c': 3, 'd': 5}})

        os.remove('/tmp/conf.yaml')
        os.remove('./conf.yaml')

    def test_ini(self):
        """Test ini merging."""
        config_finder = ConfigFinder('/tmp', '.')

        dict1 = {'a': {'e': 7}, 'b': {'c': 3, 'd': 4}}

        cfg = configparser.ConfigParser()
        for section, content in dict1.items():
            cfg.add_section(section)
            for key, val in content.items():
                cfg.set(section, key, val)
        with open('/tmp/conf.ini', 'w') as fd_:
            cfg.write(fd_)

        dict2 = {'b': {'d': 5}}
        cfg = configparser.ConfigParser()
        for section, content in dict2.items():
            cfg.add_section(section)
            for key, val in content.items():
                cfg.set(section, key, val)
        with open('./conf.ini', 'w') as fd_:
            cfg.write(fd_)

        self.assertDictEqual(config_finder('conf.ini'),
                             {'a': {'e': '7'},
                              'b': {'c': '3', 'd': '5'}})
        os.remove('/tmp/conf.ini')
        os.remove('./conf.ini')


def test_suite():
    """The suite."""
    loader = unittest.TestLoader()
    mysuite = unittest.TestSuite()
    mysuite.addTest(loader.loadTestsFromTestCase(TestRecursiveDictUpdate))
    mysuite.addTest(loader.loadTestsFromTestCase(TestConfigSearch))
    mysuite.addTest(loader.loadTestsFromTestCase(TestConfigFinder))

    return mysuite


if __name__ == '__main__':
    unittest.main()
