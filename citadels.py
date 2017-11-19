import datetime
import pytz
from bravado.exception import HTTPForbidden

from config import *
from util import esi_api, access_token, name_to_id


def check_citadels():
    """
    Check citadels for fuel and services status
    """
    corporation_id = name_to_id(CORPORATION_NAME, 'corporation')
    structures = esi_api('Corporation.get_corporations_corporation_id_structures', token=access_token, corporation_id=corporation_id)
    detonations = esi_api('Industry.get_corporation_corporation_id_mining_extractions', token=access_token, corporation_id=corporation_id)
    detonations = {d['structure_id']: d for d in detonations}
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    too_soon = datetime.timedelta(days=TOO_SOON)
    messages = []
    for structure in structures:
        structure_id = structure['structure_id']
        message = []

        # Grab structure name
        try:
            structure_info = esi_api('Universe.get_universe_structures_structure_id', token=access_token, structure_id=structure_id)
        except HTTPForbidden, e:
            messages.append('Found a citadel ({}) in {} that doesn\'t allow {} to dock!'.format(structure_id,
                                                                                                structure['system_id'],
                                                                                                CORPORATION_NAME))
            continue
        name = structure_info.get('name')

        # List online/offline services
        online_services = []
        offline_services = []
        for service in structure.get('services') or []:
            if service['state'] == 'online':
                online_services.append(service.get('name'))
            if service['state'] == 'offline':
                offline_services.append(service.get('name'))
        online = ', '.join([service for service in online_services])
        offline = ', '.join([service for service in offline_services])

        # Check when fuel expires
        fuel_expires = structure.get('fuel_expires', None)

        # Check for upcoming detonations
        try:
            detonation = detonations[structure_id]['chunk_arrival_time']
            if detonation - now < too_soon:
                message.append('Ready to detonate {}'.format(detonation))
        except KeyError:
            pass

        # Build message for fuel running out and offline services 
        if fuel_expires and (fuel_expires - now.date() < too_soon):
            message.append('Runs out of fuel on {}'.format(fuel_expires))
            if online_services:
                message.append('Online Services: {}'.format(online))
            if offline_services:
                message.append('Offline Services: {}'.format(offline))
        elif offline_services:
            message.append('Offline services: {}'.format(offline))
        if message:
            messages.append('\n'.join(['{}'.format(name)] + message))
    return messages
