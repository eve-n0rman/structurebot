from __future__ import absolute_import
import datetime
import pytz
import logging

from .config import CONFIG
from .util import esi, esi_client, name_to_id, ids_to_names
from .assets import Fitting, Asset, Type
from .universe import System
import six


logger = logging.getLogger(__name__)


class Structure(object):
    def __init__(self, structure_id, corporation_id=None, type_id=None, type_name=None,
                 system_id=None, services=None, fuel_expires=None,
                 accessible=None, name=None, state=None, state_timer_end=None,
                 detonation=None, unanchors_at=None, profile_id=None,
                 fuel=[], fitting=Fitting()):
        super(Structure, self).__init__()
        self.structure_id = structure_id
        self.corporation_id = corporation_id
        self.type_id = type_id
        self.type = Type.from_id(type_id)
        self.type_name = type_name or self.type.name
        self.system_id = system_id
        self.system = System.from_id(self.system_id)
        self.system_name = self.system.name
        self.constellation_name = self.system.constellation.name
        self.region_name = self.system.constellation.region.name
        self.fuel = fuel
        self.fuel_expires = getattr(fuel_expires, 'v', None)
        self.accessible = accessible
        self.name = name
        self.state = state
        self.state_timer_end = getattr(state_timer_end, 'v', None)
        self.detonation = getattr(detonation, 'v', None)
        self.unanchors_at = getattr(unanchors_at, 'v', None)
        self.profile_id = profile_id
        self.fitting = fitting
        self._fuel_rate = 0
        # Grab structure name
        endpoint = 'get_universe_structures_structure_id'
        structure_request = esi.op[endpoint](structure_id=structure_id)
        structure_response = esi_client.request(structure_request)
        if structure_response.status == 200:
            structure_info = structure_response.data
            self.name = structure_info.get('name')
            self.system_id = structure_info.get('system_id')
            self.type_id = structure_info.get('type_id')
            self.accessible = True
        elif structure_response.status == 403:
            self.name = "Inaccessible Structure"
            self.accessible = False
        self.online_services = []
        self.offline_services = []
        if services:
            for service in services:
                if service['state'] == 'online':
                    self.online_services.append(service.get('name'))
                if service['state'] == 'offline':
                    self.offline_services.append(service.get('name'))

    @property
    def fuel_rate(self):
        if self._fuel_rate:
            return self._fuel_rate
        if not self.fitting:
            return self._fuel_rate
        fuel_bonus = {
            # Engineering Complex
            1404: {
                # Structure Engineering Service Module
                1415: 0.75
            },
            # Refinery
            1406: {
                # Structure Resource Processing Service Module
                1322: 0.80
            },
            # Citadel
            1657: {
                # Structure Citadel Service Module
                1321: 0.75
            },
        }
        for service in self.fitting.ServiceSlot:
            hourly_fuel = [a.value for a in service.dogma_attributes
                           if a.attribute_id == 2109][0]
            try:
                if service.group_id in fuel_bonus[self.type.group_id]:
                    modifier = fuel_bonus[self.type.group_id][service.group_id]
                else:
                    modifier = 1.0
            except KeyError:
                modifier = 1.0
            self._fuel_rate += hourly_fuel*modifier
        return self._fuel_rate

    @property
    def needs_detonation(self):
        for service in self.online_services:
            if service == 'Moon Drilling' and not self.detonation:
                return True
        return False

    @property
    def detonates_soon(self):
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        if self.detonation and (self.detonation - now < CONFIG['DETONATION_WARNING']):
            return True
        return False

    @property
    def needs_ozone(self):
        if self.type_name == 'Ansiblex Jump Gate' and self.jump_fuel < CONFIG['JUMPGATE_FUEL_WARN']:
            return True
        return False

    @property
    def needs_fuel(self):
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        if self.fuel_expires and (self.fuel_expires - now < CONFIG['TOO_SOON']):
            if self.unanchoring and self.unanchors_at < self.fuel_expires:
                return False
            return True
        return False

    @property
    def jump_fuel(self):
        return sum([lo.quantity for lo in self.fuel if lo.name == 'Liquid Ozone'])

    @property
    def reinforced(self):
        if self.state in ['armor_reinforce', 'hull_reinforce']:
            return True
        return False

    @property
    def vulnerable(self):
        if self.state in ['deploy_vulnerable', 'armor_vulnerable', 'hull_vulnerable']:
            return True
        return False

    @property
    def has_core(self):
        if self.fitting.QuantumCoreRoom:
            return True
        return False

    @property
    def needs_core(self):
        if self.type.group.name.startswith('Upwell') or self.has_core:
            return False
        return True

    @property
    def unanchoring(self):
        if self.unanchors_at:
            return True
        return False

    @classmethod
    def from_corporation(cls, corporation_name, assets=None):
        structure_list = []
        corporation_id = name_to_id(corporation_name, 'corporation')
        assets = assets or Asset.from_entity_id(corporation_id, 'corporations')
        endpoint = 'get_corporations_corporation_id_structures'
        structures_request = esi.op[endpoint](corporation_id=corporation_id)
        structures_response = esi_client.request(structures_request)
        structures = structures_response.data
        endpoint = 'get_corporation_corporation_id_mining_extractions'
        detonations_request = esi.op[endpoint](corporation_id=corporation_id)
        detonations_response = esi_client.request(detonations_request)
        detonations = detonations_response.data
        detonations = {d['structure_id']: d['chunk_arrival_time']
                       for d in detonations}
        structure_keys = ['structure_id', 'corporation_id', 'system_id', 'type_id',
                          'services', 'fuel_expires', 'state', 'state_timer_end',
                          'unanchors_at', 'profile_id']
        for s in structures:
            sid = s['structure_id']
            kwargs = {k: v for k, v in s.items() if k in structure_keys}
            kwargs['type_name'] = ids_to_names([s['type_id']])[s['type_id']]
            kwargs['detonation'] = detonations.get(sid)
            structure_contents = [a for a in assets if a.location_id == sid]
            if structure_contents:
                kwargs['fitting'] = Fitting.from_assets(structure_contents)
                kwargs['fuel'] = [a for a in structure_contents if a.location_flag == 'StructureFuel']
            structure_list.append(cls(**kwargs))
        return structure_list

    def __str__(self):
        return '{} ({}) - {}'.format(self.name, self.structure_id,
                                    self.type_name)

