
import json
import os
import sys

from getpass import getpass
from argparse import ArgumentParser

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from input.generator.database import PlansGeneratorDatabase
from  icarus.util.print import Printer as pr

class PlansGenerator:
    def __init__(self, database, encoding):
        self.database = PlansGeneratorDatabase(database)
        self.encoding = encoding
        self.decoding = {name: {v: k for k, v in encoding[name].items()} 
            for name in encoding.keys()}

    @staticmethod
    def chunk(arr, n):
        for i in range(0, len(arr), n):
            yield arr[i: i+n]

    @staticmethod
    def time(secs):
        hours = secs // 3600
        secs -= hours * 3600
        mins = secs // 60
        secs -= mins * 60
        return ':'.join(str(t).zfill(2) for t in (hours, mins, secs))

    def encode_start(self, act):
        return (self.time(act[3]), self.decoding['activity'][act[4]], act[5], act[6])
    
    def encode_route(self, route):
        return (self.time(route[3]), self.decoding['mode'][route[2]])
    
    def encode_act(self, act):
        return (self.time(act[2]), self.time(act[3]),
            self.decoding['activity'][act[4]], act[5], act[6])
    
    def generate_plans(self, savepath, region=[], time=[], 
            modes=[], sample=1, bin_size=100000):
        pr.print('Beginning simulation input plans generation.', time=True)

        modes = tuple(self.encoding['mode'][mode] for mode in modes 
            if mode in self.encoding['mode'].keys())

        if len(region):
            pr.print('Fetching MAZs in the specified region.', time = True)
            mazs = self.database.get_mazs(region)
            pr.print(f'Found {len(mazs)} MAZs in specified region.', time=True)
            pr.print('Fetching agent plans occuring on selected MAZs.', time=True)
        else:
            pr.print(f'Fetching all agent plans across all MAZs.', time=True)
            mazs = []

        plans = self.database.get_plans(mazs, modes, sample)
        target = len(plans)

        pr.print(f'Found {target} plans under select conditions.', time=True)
        pr.print('Iterating over plans and generating plans file.', time=True)
        pr.print('Plans File Generation Progress', persist=True, replace=True,
            frmt='bold', progress=0)
        planfile = open(savepath, 'w')

        plan_frmt = '<person id="%s"><plan selected="yes">'
        route_frmt = '<leg trav_time="%s" mode="%s"/>'
        act_frmt = '<act start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
        start_frmt = '<act end_time="%s" type="%s" x="%s" y="%s"/>'

        total = 0
        planfile.write('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE plans'
            ' SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd"><plans>')
        for group in self.chunk(plans, bin_size):
            size = len(group)
            pr.print(f'Fetching activity and route data for {size} plans.', time=True)
            agents = tuple(plan[0] for plan in group)
            routes = list(self.database.get_routes(agents))
            activities = list(self.database.get_activities(agents))
            pr.print('Writing activity and route data to plans file.', time=True)
            for plan in group:
                planfile.write(plan_frmt % plan[0])
                planfile.write(start_frmt % self.encode_start(activities.pop(0)))
                for i in range(plan[1] // 2):
                    planfile.write(route_frmt % self.encode_route(routes.pop(0)))
                    planfile.write(act_frmt % self.encode_act(activities.pop(0)))
                planfile.write('</plan></person>')
            planfile.flush()
            total += size
            pr.print('Plans File Generation Progress', persist=True, replace=True,
                frmt='bold', progress=total/target)
        planfile.write('</plans>')
        planfile.close()

        pr.print('Plans File Generation Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print('Simulation input plans generation complete.', time=True)

if __name__ == '__main__':
    parser = ArgumentParser(prog='AgentsParser',
        description='Generate plans file for MATSIM simulation from database.')
    parser.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'))
    parser.add_argument('--log', type=str, dest='log',
        help='specify a log file location; by default the log will not be saved',
        default=None)
    args = parser.parse_args()

    try:
        if args.log is not None:
            pr.log(args.log)

        with open(args.config) as handle:
            config = json.load(handle)

        database = config['database']
        encoding = config['encoding']

        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        generator = PlansGenerator(database, encoding)

        options = ('region', 'time', 'modes', 'sample', 'bin_size')
        params = {key: config[key] for key in options if key in config}
        generator.generate_plans(config['savepath'], **params)
    
    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
        quit()
    except KeyError as err:
        print(f'Config file {args.config} is not valid config file.')
        quit()
    except Exception as err:
        raise(err)