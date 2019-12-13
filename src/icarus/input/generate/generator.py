
from icarus.input.generate.database import PlansGeneratorDatabase
from icarus.util.print import Printer as pr

class PlansGenerator:
    plan_frmt = '<person id="%s"><plan selected="yes">'
    route_frmt = '<leg trav_time="%s" mode="%s"/>'
    act_frmt = '<act start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
    start_frmt = '<act end_time="%s" type="%s" x="%s" y="%s"/>'
    end_frmt = '<act start_time="%s" type="%s" x="%s" y="%s"/>'

    def __init__(self, database, encoding):
        self.database = PlansGeneratorDatabase(database)
        self.encoding = encoding
        self.decoding = {name: {v: k for k, v in values.items()} 
            for name, values in encoding.items()}


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

    
    def encode_route(self, route):
        return self.route_frmt % (self.time(route[3]), 
            self.encoding['mode'][str(route[2])])

    
    def encode_act(self, act):
        if act[2] > 0:
            return self.act_frmt % (self.time(act[2]), self.time(act[3]),
                self.decoding['activity'][act[4]], act[5], act[6])
        else:
            return self.start_frmt % (self.time(act[3]), 
                self.decoding['activity'][act[4]], act[5], act[6])

    
    def generate_plans(self, planpath, vehiclepath, region=[], time=[], 
            modes=[], sample=1, bin_size=100000):
        pr.print('Beginning simulation input plans generation.', time=True)

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
        planfile = open(planpath, 'w')

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
                planfile.write(self.plan_frmt % plan[0])
                planfile.write(self.encode_act(activities.pop(0)))
                for i in range(plan[1] // 2):
                    planfile.write(self.encode_route(routes.pop(0)))
                    planfile.write(self.encode_act(activities.pop(0)))
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

        vehiclesfile = open(vehiclepath, 'w')
        
        vehiclesfile.write('<?xml version="1.0" encoding="UTF-8" ?>'
            '<vehicleDefinitions xmlns="http://www.matsim.org/files/dtd" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.matsim.org/files/dtd '
            'http://www.matsim.org/files/dtd/vehicleDefinitions_v1.0.xsd">')
        vehiclesfile.write('''
            <vehicleType id="Bus">
                <capacity>
                    <seats persons="70"/>
                    <standingRoom persons="0"/>
                </capacity>
                <length meter="18.0"/>
                <width meter="2.5"/>
                <accessTime secondsPerPerson="0.5"/>
                <egressTime secondsPerPerson="0.5"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="2.8"/>
            </vehicleType>''')
        vehiclesfile.write('''
            <vehicleType id="Tram">
                <capacity>
                    <seats persons="180"/>
                    <standingRoom persons="0"/>
                </capacity>
                <length meter="36.0"/>
                <width meter="2.4"/>
                <accessTime secondsPerPerson="0.25"/>
                <egressTime secondsPerPerson="0.25"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="5.2"/>
            </vehicleType>''')
        vehiclesfile.write('''
            <vehicleType id="car">
                <length meter="7.5"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="40.0"/>
                <accessTime secondsPerPerson="1.0"/>
                <egressTime secondsPerPerson="1.0"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="1.0"/>
            </vehicleType>''')
        vehiclesfile.write('''
            <vehicleType id="bike">
                <length meter="5.0"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="4.4704"/>
                <accessTime secondsPerPerson="1.0"/>
                <egressTime secondsPerPerson="1.0"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="0.25"/>
            </vehicleType> ''')
        vehiclesfile.write('''
            <vehicleType id="walk">
                <length meter="1.0"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="1.4"/>
                <accessTime secondsPerPerson="1.0"/>
                <egressTime secondsPerPerson="1.0"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="0.0"/>
            </vehicleType> ''')
        vehiclesfile.write('</vehicleDefinitions>')
        vehiclesfile.close()

        pr.print('Simulation input plans generation complete.', time=True)
