import random
import numpy as np


class PLayer:
    def __init__(self):
        pass


class Planet:

    def __init__(self, population, planet_type, name):
        self.population = population
        self.planet_type = planet_type
        self.name = name

    def planet_destroyed(self):
        pass

    def rename(self, new_name):
        self.name = new_name


class Sector:

    def __init__(self, sector_number, ports_in_sector=None, connected_sectors=None, fighters_in_sector=0, planets_in_sector=0):

        self.fighters_in_sector = fighters_in_sector
        self.sector = sector_number
        self.planets_in_sector = planets_in_sector

        if ports_in_sector == None:
            self.ports = self.generate_ports()
        else:
            self.ports = ports_in_sector

        if connected_sectors == None:
            self.connected_sectors = self.generate_connecting_sectors()
        else:
            self.connected_sectors = connected_sectors

    def load_sector(self, is_final_destination):

        if is_final_destination:
            pass
        else:
            pass

    def generate_connecting_sectors(self):

        total_connecting_sectors = random.randrange(1, 5)

        connected_sectors = {}

        for _ in range(total_connecting_sectors):

            while True:
                sector = random.randrange(1, total_sectors + 1)
                if not sector in connected_sectors:
                    break

            connected_sectors[sector] = random.randrange(
                1, 3)  # Fuel cost
        return connected_sectors

    def generate_ports(self):

        sector_ports = {}

        ports_in_system = random.randint(0, 3)

        if ports_in_system > 0:

            for port_number in range(ports_in_system):

                sector_ports[port_number] = TradePort(
                    self.sector, port_number)
        return sector_ports


class TradePort:

    def __init__(self, sector, port_number):
        self.sector = sector
        self.name = 'Trading Port {} ~ {}'.format(sector, port_number)
        # Fuel for ship/Planetary shields
        self.info = {}
        self.info['Ore'] = random.randint(10_000, 50_000)
        self.info['Organics'] = random.randint(10_000, 50_000)      # Food
        self.info['Armor'] = random.randint(
            10_000, 50_000)         # Hull Points
        self.info['Batteries'] = random.randint(10_000, 50_000)     # Ammo
        self.info['Equipment'] = random.randint(
            10_000, 50_000)     # General cargo
        # Credits that the port can use to buy products with from the player
        self.info['Credits'] = random.randint(510_000, 1_350_000)
        self.prices = self.generate_prices()

    def sell_to_port(self, quantity, item):
        pass

    def buy_from_port(self, quantity, item):
        pass

    def steal_from_port(self, quantity, item):
        pass

    def restock(self):
        self.credits += 100_000
        self.fuel_ore += 10_000
        self.organics += 10_000
        self.armor += 10_000
        self.batteries += 10_000
        self.credits += 10_000

    def generate_prices(self):
        prices = {}

        prices["Ore"] = self.info['Ore']/800
        prices["Organics"] = self.info['Organics']/1000
        prices["Equipment"] = self.info['Equipment']/250

        prices["Armor"] = self.info['Armor']/100
        prices["Batteries"] = self.info['Batteries']/4000

        return prices

    def enter_port():
        pass

    def exit_port():
        pass


def create_path(start_point, end_point, map):
    '''
        Dijkstra's algorithm used to find shortest fuel cost path 
    '''
    data = {key: {'cost': np.inf} for key in map}

    data[start_point]['cost'] = 0

    path = []

    predecessor = {}

    while map:  # While there are still items in map

        minNode = None

        for node in map:
            # Determine which of the connected nodes have the lowest cost ...initializes to start_point
            if minNode == None:
                minNode = node
            elif data[node]['cost'] < data[minNode]['cost']:
                minNode = node

        # Loop connected nodes and adjust costs to each one
        for childNode, cost in map[minNode].connected_sectors.items():

            path_cost = cost + data[minNode]['cost']

            if path_cost < data[childNode]['cost']:

                data[childNode]['cost'] = path_cost
                predecessor[childNode] = minNode

        map.pop(minNode)  # Remove the visited Node

    currentNode = end_point

    while currentNode != start_point:

        try:
            path.insert(0, currentNode)
            currentNode = predecessor[currentNode]
        except KeyError:
            print("Path not reachable")
            break

    if data[end_point]['cost'] != np.inf:   # If the endpoint is reachable
        print('Lowest Cost: ' + str(data[end_point]['cost']))
        print('Path: ' + " > ".join([str(element)
              for element in [start_point] + path]))


def generate_map(total_sectors=100):

    map = {}

    for current_sector in range(1, total_sectors+1):

        map[current_sector] = Sector(current_sector)

    return map


total_sectors = 1000
map = generate_map(total_sectors)

start = int(input("Enter the starting sector (1-{}) > ".format(total_sectors)))
end = int(input("Enter the target sector (1-{})> ".format(total_sectors)))

create_path(start, end, map)
