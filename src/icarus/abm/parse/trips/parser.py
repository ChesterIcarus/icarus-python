
import csv

from getpass import getpass
from argparse import ArgumentParser

from icarus.abm.parse.trips.database import TripsParserDatabase
from icarus.util.print import Printer as pr

class TripsParser:
    def __init__(self, database, encoding):
        self.database = TripsParserDatabase(database)
        self.encoding = encoding

    @staticmethod
    def adj_time(time):
        return int(float(time)*60)

    def parse(self, sourcepath, silent=False, resume=False, bin_size=100000):
        if not silent:
            pr.print(f'Beginning AMB trip data parsing from {sourcepath}.', time=True)
            pr.print('Creating temporary tables.', time=True)

        self.database.create_temp()

        if not silent:
            pr.print(f'Loading process metadata and resources.', time=True)

        target = sum(1 for l in open(sourcepath, 'r')) - 1
        tripsfile = open(sourcepath, 'r', newline='')
        parser = csv.reader(tripsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        trips = []
        trip_id = 0

        if resume:
            if not silent:
                pr.print('Finding where we left off last.', time=True)
            offset = self.database.count_trips()
            if not silent:
                pr.print(f'Skipping to trip {offset}.', time=True)
            for i in range(offset):
                next(parser)

        if not silent:
            pr.print('Starting trips CSV file iteration.', time=True)
            pr.print('Trips Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=trip_id/target)

        for trip in parser:
            vehicle = int(trip[cols['vehId']])            
            trips.append((
                trip_id,
                int(trip[cols['hhid']]),
                int(trip[cols['uniqueid']]),
                int(trip[cols['pnum']]),
                int(trip[cols['personTripNum']]) - 1,
                int(trip[cols['origTaz']]),
                int(trip[cols['origMaz']]),
                int(trip[cols['destTaz']]),
                int(trip[cols['destMaz']]),
                int(trip[cols['origPurp']]),
                int(trip[cols['destPurp']]),
                int(trip[cols['mode']]),
                vehicle if vehicle > 0 else 0,
                self.adj_time(trip[cols['isamAdjDepMin']]) + 16200,
                self.adj_time(trip[cols['isamAdjArrMin']]) + 16200,
                self.adj_time(trip[cols['isamAdjDurMin']])))
            trip_id += 1

            if trip_id % bin_size == 0:
                if not silent:
                    pr.print(f'Pushing {bin_size} trips to the database.', time=True)
                self.database.write_trips(trips)
                trips = []
                if not silent:
                    pr.print('Resuming CSV file parsing.', time=True)
                    pr.print('Trips Parsing Progress', persist=True, replace=True,
                        frmt='bold', progress=trip_id/target)

        if not silent:
            pr.print(f'Pushing {trip_id % bin_size} trips to the database.', time=True)
        self.database.write_trips(trips)

        if not silent:
            pr.print('Trips Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=1)
            pr.push()
            pr.print('ABM trip data parsing complete.', time=True)
            pr.print('Merging tables and dropping temporaries.', time=True)
        
        self.database.drop_table('trips')
        self.database.create_all_idxs('temp_trips', silent=True)
        self.database.join_trips()
        self.database.drop_table('temp_trips')
        del self.database.tables['temp_trips']

    def create_idxs(self, silent=False):
        if not silent:
            pr.print(f'Creating all indexes in database {self.database.db}.', time=True)
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        if not silent:
            pr.print(f'Index creating complete.', time=True)