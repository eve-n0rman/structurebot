from __future__ import absolute_import
import unittest
from structurebot import universe


class TestUniverse(unittest.TestCase):
    def test_system(self):
        system = universe.System.from_name('GE-8JV')
        self.assertEqual('GE-8JV', system.name)
        self.assertEqual('9HXQ-G', system.constellation.name)
        self.assertEqual('Catch', system.constellation.region.name)