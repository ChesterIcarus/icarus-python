
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.input.generate.generator import PlansGenerator
from icarus.util.print import Printer as pr


parser = ArgumentParser(prog='AgentsParser',
    description='Generate plans file for MATSIM simulation from database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'abm/generate/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',
    default=None)
args = parser.parse_args()

if args.log is not None:
    pr.log(args.log)

try:
    with open(args.config) as handle:
        config = json.load(handle)
except FileNotFoundError as err:
    pr.print(f'Config file {args.config} not found.', time=True)
    raise err
except json.JSONDecodeError as err:
    pr.print(f'Config file {args.config} is not valid JSON.', time=True)
    raise err
except KeyError as err:
    pr.print(f'Config file {args.config} is not valid config file.', time=True)
    raise err

database = config['database']
encoding = config['encoding']

database['password'] = getpass(
    f'SQL password for {database["user"]}@localhost: ')

generator = PlansGenerator(database, encoding)

options = ('region', 'time', 'modes', 'sample', 'bin_size')
params = {key: config[key] for key in options if key in config}
generator.generate_plans(config['planpath'], config['vehiclepath'], **params)
