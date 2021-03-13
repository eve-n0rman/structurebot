#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function
import logging
import argparse

from structurebot.citadels import Structure
from structurebot.config import CONFIG
import six


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--csv', help='Print CSV output',
                        action='store_true')
    parser.add_argument('-d', '--debug', help='Print debug output',
                        action='store_true')
    args = parser.parse_args()

    level = logging.WARNING
    if CONFIG['DEBUG'] or args.debug:
        level = logging.INFO
    logging.basicConfig(level=level)
    pyswagger_logger = logging.getLogger('pyswagger')
    pyswagger_logger.setLevel(logging.ERROR)
    structures = Structure.from_corporation(CONFIG['CORPORATION_NAME'])
    total_fuel = 0
    if args.csv:
        import csv
        import sys
        columns = [
            'structure_id',
            'type_name',
            'name',
            'state',
            'fuel_expires',
            'fuel_rate',
            'needs_fuel',
            'jump_fuel',
            'needs_core',
            'unanchoring',
            'profile_id',
            'packaged_volume',
            'system_name',
            'constellation_name',
            'region_name'
        ]
        writer = csv.writer(sys.stdout)
        writer.writerow(columns)
    for structure in sorted(structures, key=lambda x: x.name):
        if args.csv:
            writer.writerow([getattr(structure, c)
                             for c in columns])
        else:
            print(structure)
            print('Fuel/Cycle: {}'.format(structure.fuel_rate))
            print(structure.fitting)
            print('-----')
            total_fuel += structure.fuel_rate
    if not args.csv:
        print('Total fuel/cycle: {}'.format(total_fuel))
