from __future__ import absolute_import
import unittest
import doctest
import datetime as dt
import pytz
from pyswagger.primitives import Datetime
from structurebot import citadels
from structurebot import assets
from structurebot.config import CONFIG
from structurebot.util import name_to_id


class TestStructures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        corp = CONFIG['CORPORATION_NAME']
        cls.structures = citadels.Structure.from_corporation(corp)

    def test_structures(self):
        self.assertGreater(len(self.structures), 0)
        for structure in self.structures:
            self.assertIsInstance(structure, citadels.Structure)
            self.assertIsInstance(structure.fitting, assets.Fitting)


class TestStructureDogma(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raitaru_type = assets.Type.from_name('Raitaru')
        ansiblex_type = assets.Type.from_name('Ansiblex Jump Gate')
        athanor_type = assets.Type.from_name('Athanor')
        manufacturing_type = assets.Type.from_name('Standup Manufacturing Plant I')
        drill_type = assets.Type.from_name('Standup Moon Drill I')
        research_type = assets.Type.from_name('Standup Research Lab I')
        quantum_core = assets.Type.from_name('Raitaru Upwell Quantum Core')
        fuel_expires = Datetime()
        now = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
        fuel_expires.apply_with(None, now + dt.timedelta(days=3), None)
        raitaru_fitting = assets.Fitting(ServiceSlot=[manufacturing_type,
                                                      research_type],
                                         QuantumCoreRoom=[quantum_core])
        uncored_fitting = assets.Fitting(ServiceSlot=[manufacturing_type,
                                                      research_type])
        cls.raitaru = citadels.Structure(1, type_id=raitaru_type.type_id,
                                         type_name=raitaru_type.name,
                                         fitting=raitaru_fitting,
                                         fuel_expires=fuel_expires)
        cls.unfit_raitaru = citadels.Structure(2, type_id=raitaru_type.type_id,
                                               type_name=raitaru_type.name)
        unanchors_at = Datetime()
        unanchors_at.apply_with(None, now + dt.timedelta(days=2), None)
        cls.unanchoring_raitaru = citadels.Structure(2, type_id=raitaru_type.type_id,
                                                     type_name=raitaru_type.name,
                                                     fitting=uncored_fitting,
                                                     fuel_expires=fuel_expires,
                                                     unanchors_at=unanchors_at)
        raitaru_no_core_fitting = assets.Fitting(ServiceSlot=[manufacturing_type,
                                                              research_type])
        cls.no_core_raitaru = citadels.Structure(2, type_id=raitaru_type.type_id,
                                                 type_name=raitaru_type.name,
                                                 fitting=raitaru_no_core_fitting)
        cls.ansiblex = citadels.Structure(3, type_id=ansiblex_type.type_id,
                                          type_name=ansiblex_type.name)
        detonates_at = Datetime()
        detonates_at.apply_with(None, now + dt.timedelta(hours=12), None)
        long_detonates_at = Datetime()
        long_detonates_at.apply_with(None, now + dt.timedelta(days=21), None)
        athanor_fitting = assets.Fitting(ServiceSlot=[drill_type])
        drill_service = {'name': 'Moon Drilling', 'state': 'online'}
        cls.detonating_athanor = citadels.Structure(3, type_id=athanor_type.type_id,
                                                     type_name=athanor_type.name,
                                                     fitting=athanor_fitting,
                                                     services=[drill_service],
                                                     detonation=detonates_at)
        cls.long_detonating_athanor = citadels.Structure(4, type_id=athanor_type.type_id,
                                                         type_name=athanor_type.name,
                                                         fitting=athanor_fitting,
                                                         services=[drill_service],
                                                         detonation=long_detonates_at)
        cls.unscheduled_athanor = citadels.Structure(5, type_id=athanor_type.type_id,
                                                     type_name=athanor_type.name,
                                                     fitting=athanor_fitting,
                                                     services=[drill_service])
        

    def test_fitting(self):
        self.assertTrue(self.raitaru.fitting)
        self.assertFalse(self.unfit_raitaru.fitting)

    def test_fuel(self):
        self.assertEqual(self.raitaru.fuel_rate, 18)
        # Do twice to test caching
        self.assertEqual(self.raitaru.fuel_rate, 18)
        self.assertTrue(self.raitaru.needs_fuel)
        # Test unfit structure
        self.assertEqual(self.unfit_raitaru.fuel_rate, 0)
        self.assertFalse(self.unfit_raitaru.needs_fuel)
        # Test unanchoring with enough fuel
        self.assertFalse(self.unanchoring_raitaru.needs_fuel)

    def test_unanchoring(self):
        self.assertTrue(self.unanchoring_raitaru.unanchoring)
        self.assertFalse(self.raitaru.unanchoring)

    def test_core(self):
        self.assertFalse(self.raitaru.needs_core)
        self.assertTrue(self.no_core_raitaru.needs_core)
        self.assertFalse(self.ansiblex.needs_core)

    def test_detonations(self):
        self.assertFalse(self.detonating_athanor.needs_detonation)
        self.assertTrue(self.unscheduled_athanor.needs_detonation)
        self.assertTrue(self.detonating_athanor.detonates_soon)
        self.assertFalse(self.unscheduled_athanor.detonates_soon)
        self.assertFalse(self.raitaru.detonates_soon)
        self.assertFalse(self.long_detonating_athanor.detonates_soon)

    def test_inaccessible(self):
        goonstar = citadels.Structure(1022734985679, type_id=35834)
        self.assertEqual(goonstar.name, 'Inaccessible Structure')
        self.assertFalse(goonstar.accessible)

    def test_accessible(self):
        bravestar = citadels.Structure(1032110505696, type_id=35834)
        self.assertEqual(str(bravestar), 'GE-8JV - Mothership Bellicose -R (1032110505696) - Keepstar')
        self.assertTrue(bravestar.accessible)