
import os
import shapefile
import requests
import logging as log

from typing import List
from argparse import ArgumentParser
from pyproj import Transformer, Geod

from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil
from icarus.util.general import counter


class Node:
    __slots__ = ('x', 'y')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class Link:
    __slots__ = ('source_node', 'terminal_node', 'length')

    def __init__(self, source_node: Node, terminal_node: Node, length: float):
        self.source_node = source_node
        self.terminal_node = terminal_node
        self.length = length


def get_wkt_string(epsg: int):
    res = requests.request('get', f'https://epsg.io/{epsg}.prettywkt')
    string = res.content.decode().replace(' ', '').replace('\n', '')
    return string


def get_proj_string(epsg: int):
    res = requests.request('get', f'https://epsg.io/{epsg}.proj4')
    string = res.content.decode().replace('\n', '')
    return string


def export_routes(database: SqliteUtil, modes: List[str], 
        filepath: str, skip_empty: bool, epsg: int = 2223):

    transformer = Transformer.from_crs('epsg:2223', 
        f'epsg:{epsg}', always_xy=True, skip_equivalent=True)
    transform = transformer.transform

    measurer = Geod(f'epsg:{epsg}')
    measure = lambda n1, n2: measurer.inv([n1.y], [n1.x], [n2.y], [n2.x])

    prjpath = os.path.splitext(filepath)[0] + '.prj'
    with open(prjpath, 'w') as prjfile:
        info = get_wkt_string(epsg)
        prjfile.write(info)

    log.info('Loading network node data.')
    query = '''
        SELECT
            node_id,
            point
        FROM nodes;
    '''
    nodes = {}
    database.cursor.execute(query)
    result = counter(database.fetch_rows(), 'Loading node %s.')

    for node_id, point in result:
        x, y = transform(*map(float, point[7:-1].split(' ')))
        nodes[node_id] = Node(x, y)
    
    log.info('Loading network link data.')
    query = '''
        SELECT 
            link_id,
            source_node,
            terminal_node
        FROM links;
    '''
    links = {}
    database.cursor.execute(query)
    result = counter(database.fetch_rows(), 'Loading link %s.')

    for link_id, source_node, terminal_node in result:
        src_node = nodes[source_node]
        term_node = nodes[terminal_node]
        length = measure(src_node, term_node)
        links[link_id] = Link(src_node, term_node, length)


    log.info('Loading network routing data.')
    query = f'''
        SELECT
            output_legs.leg_id,
            output_legs.agent_id,
            output_legs.agent_idx,
            output_legs.mode,
            output_legs.duration,
            GROUP_CONCAT(output_events.link_id, " ")
        FROM output_legs
        LEFT JOIN output_events
        ON output_legs.leg_id = output_events.leg_id
        WHERE output_legs.mode IN {tuple(modes)}
        GROUP BY
            output_legs.leg_id
        ORDER BY
            output_events.leg_id,
            output_events.leg_idx;
    '''
    database.cursor.execute(query)
    result = counter(database.fetch_rows(block=1000000),
        'Exporting route %s.')

    routes = shapefile.Writer(filepath)
    routes.field('leg_id', 'N')
    routes.field('agent_id', 'N')
    routes.field('agent_idx', 'N')
    routes.field('mode', 'C')
    routes.field('duration', 'N')
    routes.field('length', 'N')

    log.info('Exporting simulation routes to shapefile.')
    for leg_id, agent_id, agent_idx, mode, duration, events in result:
        if events is not None:
            route = [links[l] for l in events.split(' ')]
            line = [(link.source_node.x, link.source_node.y) for link in route]
            line.append((route[-1].terminal_node.x, route[-1].terminal_node.y))
            length = sum((link.length for link in route))
            routes.record(leg_id, agent_id, agent_idx, mode, duration, length)
            routes.line([line])
        elif not skip_empty:
            routes.record(leg_id, agent_id, agent_idx, mode, duration, None)
            routes.null()

    if routes.recNum != routes.shpNum:
        log.error('Record/shape misalignment; internal exporting failure.')

    routes.close()

    log.info(f'Routing export complete: wrote {routes.shpNum} routes.')


def main():
    parser = ArgumentParser()
    main = parser.add_argument_group('main')
    main.add_argument('file', type=str,
        help='file path to save the exported routes to')
    main.add_argument('--modes', type=str, nargs='+', dest='modes',
        help='list of modes to export routes for; defualt is all modes',
        default=('walk', 'pt', 'car', 'bike'),
        choices=('walk', 'pt', 'car', 'bike'))
    main.add_argument('--skip-empty', dest='skip', action='store_true', default=False,
        help='skip all legs that do not have routes')
    main.add_argument('--epsg', dest='epsg', type=int, default=2223,
        help='epsg system to convert routes to; default is 2223')

    common = parser.add_argument_group('common')
    common.add_argument('--folder', type=str, dest='folder', default='.',
        help='file path to the directory containing Icarus run data'
            '; default is the working directory')
    common.add_argument('--log', type=str, dest='log', default=None,
        help='file path to save the process log; by default the log is not saved')
    common.add_argument('--level', type=str, dest='level', default='info',
        help='verbosity level of the process log; default is "info"',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
    common.add_argument('--replace', dest='replace', action='store_true', default=False,
        help='automatically replace existing data; do not prompt the user')
    args = parser.parse_args()

    handlers = []
    handlers.append(log.StreamHandler())
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    path = lambda x: os.path.abspath(os.path.join(args.folder, x))
    home = path('')

    log.info('Running route export tool.')
    log.info(f'Loading run data from {home}.')

    database = SqliteUtil(path('database.db'), readonly=True)
    config = ConfigUtil.load_config(path('config.json'))

    try:
        export_routes(database, args.modes, args.file, args.skip, args.epsg)
    except:
        log.exception('Critical error while exporting routes:')
        exit(1)

    database.close()


if __name__ == '__main__':
    main()