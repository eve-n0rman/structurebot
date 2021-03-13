from __future__ import absolute_import
import unittest
import doctest
import pytest
import structurebot.assets
from structurebot.assets import Fitting, Asset, Type, Category, Group, BaseType
from structurebot.config import CONFIG
from structurebot.util import HTTPError
from six.moves import range


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(structurebot.assets))
    return tests


class TestAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = CONFIG['CORPORATION_NAME']
        cls.assets = list(Asset.from_entity_name(name))
        cls.fittings = []
        test_mod = Asset.from_name('Standup Target Painter I')
        for n in range(1, 3):
            fitting = Fitting(MedSlot=[test_mod for x in range(0, n)])
            cls.fittings.append(fitting)
        for n in range(1, 3):
            test_fighter = Asset.from_name('Standup Einherji I', quantity=n)
            fitting = Fitting(MedSlot=[test_mod],
                              FighterBay=[test_fighter])
            cls.fittings.append(fitting)

    def test_category(self):
        cats = Category.from_ids([1, 2])
        for cat in cats:
            self.assertIsInstance(cat, Category)
        with pytest.raises(ValueError):
            Category.from_id('string')
        with pytest.raises(HTTPError):
            Category.from_id(9999)

    def test_group(self):
        groups = Group.from_ids([1,2])
        for group in groups:
            self.assertIsInstance(group, Group)
        with pytest.raises(ValueError):
            Group.from_id('string')
        with pytest.raises(HTTPError):
            Group.from_id(9999)

    def test_basetype(self):
        basetypes = BaseType.from_ids([0,2])
        for basetype in basetypes:
            self.assertIsInstance(basetype, BaseType)
        with pytest.raises(ValueError):
            BaseType.from_id('string')
        with pytest.raises(HTTPError):
            BaseType.from_id(99999)

    def test_group_category(self):
        control_tower = Type.from_name('Amarr Control Tower')
        self.assertEqual(control_tower.group.name, 'Control Tower')
        self.assertEqual(control_tower.group.category.name, 'Starbase')

    def test_assets(self):
        self.assertGreater(len(self.assets), 1)

    def test_fitting_str(self):
        self.assertEqual(str(self.fittings[-1]),
                         'FighterBay: Standup Einherji I (2)\n'
                         'MedSlot: Standup Target Painter I')

    def test_fitting_equality(self):
        self.assertEqual(self.fittings[0], self.fittings[0])
        self.assertNotEqual(self.fittings[0], self.fittings[1])
        self.assertGreaterEqual(self.fittings[0], self.fittings[0])
        self.assertLessEqual(self.fittings[0], self.fittings[0])

    def test_fitting_less(self):
        self.assertLess(self.fittings[0], self.fittings[1])
        self.assertLessEqual(self.fittings[0], self.fittings[1])
        self.assertFalse(self.fittings[0] > self.fittings[1])
        self.assertFalse(self.fittings[0] >= self.fittings[1])

    def test_fitting_greater(self):
        self.assertGreater(self.fittings[1], self.fittings[0])
        self.assertGreaterEqual(self.fittings[1], self.fittings[0])
        self.assertFalse(self.fittings[1] < self.fittings[0])
        self.assertFalse(self.fittings[1] <= self.fittings[0])

    def test_fitting_less_quantity(self):
        self.assertLess(self.fittings[2], self.fittings[3])
        self.assertLessEqual(self.fittings[2], self.fittings[3])
        self.assertFalse(self.fittings[2] > self.fittings[3])
        self.assertFalse(self.fittings[2] >= self.fittings[3])

    def test_fitting_greater_quantity(self):
        self.assertGreater(self.fittings[3], self.fittings[2])
        self.assertGreaterEqual(self.fittings[3], self.fittings[2])
        self.assertFalse(self.fittings[3] < self.fittings[2])
        self.assertFalse(self.fittings[3] <= self.fittings[2])

    def test_fitting_bad_compare(self):
        with pytest.raises(NotImplementedError):
            self.fittings[0] == 'not a fitting'

    def test_fitting_volume(self):
        self.assertEqual(self.fittings[0].packaged_volume, 4000)
        self.assertEqual(self.fittings[1].packaged_volume, 8000)
        self.assertEqual(self.fittings[2].packaged_volume, 6000)
        self.assertEqual(self.fittings[3].packaged_volume, 8000)