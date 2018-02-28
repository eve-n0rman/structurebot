import sqlite3
import json
from collections import Counter

from config import CONFIG
from util import esi, esi_client


class Fitting(object):
    """docstring for Fitting"""

    slots = ['Cargo', 'DroneBay', 'FighterBay', 'FighterTube', 'HiSlot', 'LoSlot', 'MedSlot', 'RigSlot', 'ServiceSlot', 'SubSystemSlot']

    def __init__(self, Cargo=[], DroneBay=[], FighterBay=[], FighterTube=[], HiSlot=[], LoSlot=[], MedSlot=[], RigSlot=[], ServiceSlot=[], SubSystemSlot=[]):
        super(Fitting, self).__init__()
        self.Cargo = Cargo
        self.DroneBay = DroneBay
        self.FighterBay = FighterBay
        self.FighterTube = FighterTube
        self.HiSlot = HiSlot
        self.LoSlot = LoSlot
        self.MedSlot = MedSlot
        self.RigSlot = RigSlot
        self.ServiceSlot = ServiceSlot
        self.SubSystemSlot = SubSystemSlot

    @classmethod
    def from_assets(cls, assets):
        fittings = {slot: [] for slot in Fitting.slots}
        for asset in assets:
            flag = asset.get('location_flag')
            if not flag:
                continue
            for slot in Fitting.slots:
                if flag.startswith(slot):
                    fittings[slot].append(asset)
                    fit = True
        return cls(**fittings)

    @staticmethod
    def _name_count(asset):
        name = asset.get('typeName')
        if asset.get('quantity') > 1:
            name += ' ({})'.format(asset.get('quantity'))
        return name

    def __cmp__(self, other):
        if not isinstance(other, Fitting):
            raise NotImplemented
        equality = 0
        for slot in Fitting.slots:
            item_counts = {i['type_id']: i['quantity']-1 for i in getattr(self, slot)}
            items = Counter([i['type_id'] for i in getattr(self, slot)])
            items.update(item_counts)
            other_item_counts = {i['type_id']: i['quantity']-1 for i in getattr(other, slot)}
            other_items = Counter([i['type_id'] for i in getattr(other, slot)])
            other_items.update(other_item_counts)
            items.subtract(other_items)
            for item, count in items.iteritems():
                if count < 0:
                    return -1
                if count > 0:
                    equality += count
        return equality

    def __str__(self):
        slot_strings = []
        for slot in Fitting.slots:
            slot_strs = [Fitting._name_count(i) for i in getattr(self, slot, {}) if i]
            if slot_strs:
                slot_str = ', '.join(sorted(slot_strs))
                slot_strings.append('{}: {}'.format(slot, slot_str))
        return '\n'.join(sorted(slot_strings))


class CorpAssets(object):
    """Collection of corporation assets
    
    Attributes:
        asset_tree (dict): Assets tree keyed by location_id, rooted in solar systems or unknown locations
        assets (dict): Assets keyed by item_id
        categories (dict): Nested assets tree keyed by category_id, group_id, and type_id
        corp_id (integer): corp id
        stations (dict): Assets keyed by station id
        structures (dict): Assets keyed by structure id
        types (dict): Assets keyed by type id
    """
    def __init__(self, corp_id):
        super(CorpAssets, self).__init__()
        self.corp_id = corp_id
        self.assets = {}
        self.asset_tree = {}
        self.structures = {}
        self.stations = {}
        self.types = {}
        type_annotation = {}
        self.categories = {}
        corp_assets = esi.op['get_corporations_corporation_id_assets'](corporation_id=corp_id)
        assets_response = esi_client.request(corp_assets, raw_body_only=True)
        assets_api = json.loads(assets_response.raw)
        if assets_response.header['X-Pages'][0] > 1:
            pages = assets_response.header['X-Pages'][0]
            requests = []
            for page in range(2, pages+1):
                requests.append(esi.op['get_corporations_corporation_id_assets'](
                    corporation_id=corp_id, page=page))
            responses = esi_client.multi_request(requests)
            for request,response in responses:
                assets_api += json.loads(response.raw)
        conn = sqlite3.connect('sqlite-latest.sqlite')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        type_ids = set([asset['type_id'] for asset in assets_api])
        param_holder = ','.join('?'*len(type_ids))
        query = """select * from invTypes as i \
                join invGroups as g on i.groupID=g.groupID \
                join invCategories as c on g.categoryID=c.categoryID \
                where i.typeID in ({})""".format(param_holder)
        # builds a category/group/type tree for easier filtering later on
        for row in cur.execute(query, tuple(type_ids)):
            type_dict = dict(row)
            category = self.categories.setdefault(type_dict['categoryID'], {})
            category['categoryName'] = type_dict['categoryName']
            group = category.setdefault(type_dict['groupID'], {})
            group['groupName'] = type_dict['groupName']
            group['typeID'] = type_dict
            self.types[type_dict['typeID']] = type_dict
            type_annotation[type_dict['typeID']] = type_dict.copy()
        # annotates asset with SDE info and indexes by item id
        for asset in assets_api:
            asset.update(type_annotation[asset['type_id']])
            self.assets[asset['item_id']] = asset
            type_entry = self.types[asset['type_id']].setdefault('children', [])
            type_entry.append(asset)
        # build a location tree
        for item_id, asset in self.assets.iteritems():
            location_id = asset['location_id']
            parent = None
            try:
                parent = self.assets[location_id]
            except KeyError:
                # Solar System
                if location_id >= 30000000 and location_id < 32000000:
                    parent = self.asset_tree.setdefault(location_id, {})
                # Stations/Outposts
                if location_id >= 60000000 and location_id < 64000000:
                    try:
                        parent = self.stations[location_id]
                    except KeyError:
                        get_station_id = esi.op['get_universe_stations_station_id'](station_id=location_id)
                        station = json.loads(esi_client.request(get_station_id, raw_body_only=True).raw)
                        system = self.asset_tree.setdefault(station['system_id'], {})
                        station['parent'] = system
                        parent = station
                        self.stations[location_id] = station
                # Probably a structure
                if location_id >= 1000000000000:
                    try:
                        parent = self.structures[location_id]
                    except KeyError:
                        # Someone elses structure?
                        get_structure_id = esi.op['get_universe_structures_structure_id'](structure_id=location_id)
                        structure_response = esi_client.request(get_structure_id, raw_body_only=True)
                        if structure_response.status in [403, 404]:
                            parent = self.asset_tree.setdefault(location_id, {})
                        else:
                            structure = json.loads(structure_response.raw)
                            system = self.asset_tree.setdefault(structure['solar_system_id'], {})
                            structure['parent'] = system
                            parent = structure
                            self.structures[location_id] = structure
            parent.setdefault('children', []).append(asset)

if __name__ == '__main__':
        from random import sample
        from citadels import Structure
        from copy import deepcopy
        structures = list(Structure.from_corporation(CONFIG['CORPORATION_NAME']))
        fittings = sample(structures, 1)
        test_mod = {'type_id': 35947, 'typeName': 'Standup Target Painter I', 'quantity': 1}
        for n in range(1,3):
            copied = deepcopy(fittings[0])
            copied.fitting.MedSlot.extend([test_mod]*n)
            fittings.append(copied)
        test_fighter = {'type_id': 47140,
                        'typeName': 'Standup Einherji I',
                        'quantity': 1}
        fittings[2].fitting.FighterBay.append(test_fighter)
        more_fighters = deepcopy(fittings[2])
        more_fighters.fitting.FighterBay[0]['quantity'] += 1
        fittings.append(more_fighters)
        print(fittings[3].fitting > fittings[2].fitting)
