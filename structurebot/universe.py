from __future__ import absolute_import

from .util import esi, esi_client, name_to_id, HTTPError


class EsiLocation(object):
    @classmethod
    def from_id(cls, id):
        """Base utility class to pull ESI universe info by id

        Args:
            id (int): location ESI ID

        Raises:
            ValueError: ID must be an int
            HTTPError: ESI failure

        Returns:
            cls: child class populated from ESI
        """
        id_op = cls.id_op
        id_arg = {cls.id_arg: id}
        if not isinstance(id, int):
            raise ValueError('ID must be an integer')
        type_request = esi.op[id_op](**id_arg)
        type_response = esi_client.request(type_request)
        if type_response.status == 200:
            return cls(**type_response.data)
        else:
            raise HTTPError(type_response.data['error'])

    @classmethod
    def from_name(cls, name):
        """Base utility class to pull ESI universe info by name

        Args:
            name (str): EVE universe name (region, constellation or system)

        Returns:
            cls: child class populated from ESI
        """
        id = name_to_id(name, cls.name_arg)
        return cls.from_id(id)


class Region(EsiLocation):    
    id_op = 'get_universe_regions_region_id'
    id_arg = 'region_id'
    name_arg = 'region'

    def __init__(self, region_id, name, **kwargs):
        """EVE Region

        Args:
            region_id (int): EVE region id
            name (str): EVE region name
        """
        self.region_id = region_id
        self.name = name


class Constellation(EsiLocation):
    id_op = 'get_universe_constellations_constellation_id'
    id_arg = 'constellation_id'
    name_arg = 'constellation'

    def __init__(self, constellation_id, region_id, name, **kwargs):
        """EVE Constellation

        Args:
            constellation_id (int): EVE constellation id
            region_id (int): EVE region id
            name (str): EVE constellation name
        """
        self.constellation_id = constellation_id
        self.region_id = region_id
        self.region = Region.from_id(self.region_id)
        self.name = name


class System(EsiLocation):
    id_op = 'get_universe_systems_system_id'
    id_arg = 'system_id'
    name_arg = 'solar_system'

    def __init__(self, system_id, constellation_id, name, **kwargs):
        """EVE System

        Args:
            system_id (int): EVE system id
            constellation_id (int): EVE constellation id
            name (str): EVE system name
        """
        self.system_id = system_id
        self.constellation_id = constellation_id
        self.constellation = Constellation.from_id(self.constellation_id)
        self.name = name
