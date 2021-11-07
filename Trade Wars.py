import random
import numpy as np
#import copy
import time

prompt_breaker = "____________________________________________________________________"


class Player:

    def __init__(self, current_sector, credits=20_000, cargo_holds=3_000, turns_remaining=10_000):
        self.current_sector = current_sector
        self.credits = credits
        self.cargo_holds = cargo_holds
        self.cargo = {'Ore': 0, "Organics": 0, "Equipment": 0, 'Armor': 0}
        self.fuel = turns_remaining
        self.warping = False

    def holds_available(self):

        holds_used = 0
        for value in self.cargo.values():
            holds_used += value

        return self.cargo_holds-holds_used

    def avoid_list(self, avoided_sectors):

        return avoided_sectors

    def check_input(self, action):

        print(prompt_breaker)

        if action[0] == 'm':

            if len(action) > 1:
                dest = action[1:].replace(" ", "")
                if dest.isdigit():
                    dest = int(dest)
                else:
                    dest = None
            else:

                nearby_sectors = " | ".join(
                    [str(element) for element in list(map[self.current_sector].connected_sectors.keys())])

                print('[Nearby Warps] : ' + nearby_sectors + '\n')

                dest = None

            self.move_sectors(dest)

        elif action.isdigit():

            action = int(action)

            sector_obj = map[self.current_sector]
            sector_obj.ports[action].enter_port(self)

            sector_obj.load_sector()

    def move_sectors(self, destination=None):

        start = self.current_sector

        print(f'Current Sector:\t{start}')

        while True:

            if destination == None or not destination in range(1, total_sectors+1):

                try:
                    print("Press 0 to return to the previous menu")
                    end = int(
                        input("Enter target sector (1-{})> ".format(total_sectors)))
                    break
                except:
                    print("Please input a number.")
            else:
                end = destination
                break

        if end == 0:
            return
        elif 1 <= end <= total_sectors:

            sectors_to_load = create_path(start, end, map)

            #print('Lowest Cost: ' + str(data[end_point]['cost']))

            print('Path: ' + " > ".join([str(element)
                                        for element in [self.current_sector] + sectors_to_load]))

            for sector in sectors_to_load:

                final_sector = True if sector == end else False

                if self.fuel-map[self.current_sector].connected_sectors[sector] > 0:

                    time.sleep(1)
                   # Subtract the cost to travel to the sector
                    self.fuel -= \
                        map[self.current_sector].connected_sectors[sector]

                    self.current_sector = sector

                    map[sector].load_sector()

                else:
                    print("Not enough Fuel.")
                    break

                if final_sector == True:
                    print(f'Fuel remaining: {self.fuel}\n')

        else:
            print("Input a valid number.")


class Planet:

    def __init__(self, population, planet_type, name):
        self.population = population
        self.planet_type = planet_type
        self.name = name

    def rename(self, new_name):
        self.name = new_name


class Sector:

    def __init__(self, sector_number, ports_in_sector=None, connected_sectors=None, fighters_in_sector=0, planets_in_sector=0):

        self.fighters_in_sector = fighters_in_sector
        self.sector = sector_number
        self.planets_in_sector = planets_in_sector

        if ports_in_sector == None and sector_number != 1:
            self.ports = self.generate_ports()
        else:
            self.ports = ports_in_sector

        if connected_sectors == None:
            self.connected_sectors = self.generate_connecting_sectors()
        else:
            self.connected_sectors = connected_sectors

    def load_sector(self):

        print(f'\n[\t\tSector:\t{self.sector}\t\t]\n')

        try:
            if len(self.ports) > 0:

                for num, port in enumerate(self.ports.values()):
                    print(f'({num+1}) {port.name}')
        except:
            print("Hello")

        print(prompt_breaker)

    def generate_connecting_sectors(self):

        total_connecting_sectors = random.randrange(4, 10)

        connected_sectors = {}

        for _ in range(total_connecting_sectors):

            while True:
                sector = random.randint(1, total_sectors)
                if not sector in connected_sectors:
                    break

            connected_sectors[sector] = random.randrange(
                1, 3)  # Fuel cost

        return connected_sectors

    def generate_ports(self):

        sector_ports = {}

        ports_in_system = random.randint(1, 3)

        if ports_in_system > 0:

            for port_number in range(1, ports_in_system+1):

                sector_ports[port_number] = TradePort(
                    self.sector, port_number)
        return sector_ports


class TradePort:

    def __init__(self, sector, port_number):
        self.sector = sector
        self.name = 'Trading Port {} ~ {}'.format(sector, port_number)
        # Fuel for ship/Planetary shields
        self.credits = random.randint(2_510_000, 9_700_000)
        self.inventory = self.generate_info()

    def generate_info(self):

        info = {}

        for field in ["Ore", "Organics", "Armor", "Batteries", "Equipment"]:
            info[field] = {}

        info['Ore']['Quantity'] = random.randint(30_000, 150_000)
        info['Organics']['Quantity'] = random.randint(
            40_000, 200_000)      # Food
        info['Armor']['Quantity'] = random.randint(
            10_000, 30_000)         # Hull Points
        info['Batteries']['Quantity'] = random.randint(
            60_000, 100_000)     # Ammo
        info['Equipment']['Quantity'] = random.randint(
            10_000, 45_000)     # General cargo

        return self.generate_prices(info)

    def enter_port(self, player):

        while True:

            self.inventory = self.generate_prices(self.inventory)

            # Print Quantities of items and there Buy/Sell price
            print(
                f"Current Inventory\t\tAvailable Credits: {player.credits}")

            print(prompt_breaker)

            for item, cargo in self.inventory.items():
                # Print the ports current inventory and corresponding
                # Prices to the screen

                printed_string = f'{item} : {cargo["Quantity"]}'

                if len(printed_string) <= 15:
                    tabs = "\t\t\t"
                else:
                    tabs = "\t\t"

                print(f'{printed_string}{tabs}Price: {cargo["Price"]}')

            print(prompt_breaker)

            user_selection = int(
                input("Select an option: (1) Buy from Port | (2) Sell to Port | (0) Exit port: \t"))

            print(prompt_breaker + "\n")

            if user_selection == 2:

                try:
                    item, quantity = self.buy_sell_prompt(False, player)
                except:
                    # If the user presses 0 to cancel their selection
                    continue

                self.sell_to_port(quantity, item, player)

            elif user_selection == 1:

                try:
                    item, quantity = self.buy_sell_prompt(True, player)
                except:
                    # If the user presses 0 to cancel their selection
                    continue

                self.buy_from_port(quantity, item, player)

            elif user_selection == 0:

                break

            else:
                print("Invalid selection")

            print(prompt_breaker)

    def buy_sell_prompt(self, buying, player):

        sell_or_buy = "buy" if buying == True else "sell"

        for num, key in enumerate(self.inventory):

            if num == 0:
                tabs = "\t" * 4
            else:
                tabs = "\t"*3

            item_quantity_in_holds = player.cargo.setdefault(key, 0)

            print(f'{num + 1} - {key}{tabs}On ship: {item_quantity_in_holds}')

        print("\n0 - Exit Menu\n")
        print(prompt_breaker)

        selection = int(input(f"What would you like to {sell_or_buy}?\t"))

        if selection == 0:
            return
        else:

            print(prompt_breaker)
            # String representing the commodity chosen
            commodity = list(self.inventory.keys())[selection - 1]

            commodity_price = self.inventory[commodity]['Price']

            if buying:

                player_can_afford = int(player.credits/commodity_price)

                available_units = min(player.holds_available(
                ), player_can_afford, self.inventory[commodity]['Quantity'])

            else:

                port_can_afford = int(self.credits/commodity_price)

                available_units = min(player.cargo[commodity], port_can_afford)

            while True:

                try:
                    #print("Press 0 to return to the previous menu")
                    print(
                        f'{commodity} units available for purchase: {available_units}')

                    quantity = int(
                        input(f"\nHow many units would you like to {sell_or_buy}? \t"))

                    transaction_cost = commodity_price * quantity

                    sign = "-" if buying == True else"+"

                    print(
                        f'\nCurrent Balance: {player.credits} || New Balance: {player.credits + (-1* transaction_cost if buying else transaction_cost) } || Change: {sign} {transaction_cost}\n')

                    selection = input(
                        "Press Enter to confirm or 0 to cancel transaction.")

                    if selection == "":

                        if quantity in range(0, available_units+1):

                            if quantity == 0:
                                return
                            else:
                                break
                        else:
                            print(
                                "Please input a number less than or equal to the number of holds available.")
                    else:
                        return
                except:
                    print("Please input a number.")

            return commodity, quantity

    def sell_to_port(self, quantity, item, player):

        commodity = self.inventory[item]

        transaction_cost = quantity * commodity['Price']

        if transaction_cost <= self.credits:
            commodity["Quantity"] += quantity
            player.cargo[item] -= quantity
            self.credits -= transaction_cost
            player.credits += transaction_cost

    def buy_from_port(self, quantity, item, player):

        commodity = self.inventory[item]

        transaction_cost = quantity * commodity['Price']

        if quantity <= commodity['Quantity'] and transaction_cost <= player.credits:

            commodity["Quantity"] -= quantity

            player.cargo[item] += quantity

            self.credits += transaction_cost
            player.credits -= transaction_cost

    def steal_from_port(self, quantity, item):
        pass

    def restock(self):
        self.credits += 100_000
        self.fuel_ore += 10_000
        self.organics += 10_000
        self.armor += 10_000
        self.batteries += 10_000
        self.credits += 300_000

    def generate_prices(self, info):

        info["Ore"]["Price"] = info['Ore']['Quantity']/1000 + 200

        info["Organics"]["Price"] = info['Organics']['Quantity']/2000 + 100

        info["Equipment"]["Price"] = info['Equipment']['Quantity'] / 500 + 1000

        info["Armor"]["Price"] = info['Armor']['Quantity'] / 800 + 4000

        info["Batteries"]["Price"] = info['Batteries']['Quantity'] / 15000 + 10

        for value in info.values():
            value["Price"] = round(value["Price"], 3)

        return info


def create_path(start_point, end_point, map):
    '''
        Dijkstra's algorithm used to find shortest fuel cost path 
    '''

    data = {key: {'cost': np.inf} for key in map}

    data[start_point]['cost'] = 0

    path = []

    predecessor = {}

    n_map = {sector: map[sector].connected_sectors.copy() for sector in map}

    while n_map:  # While there are still items in map

        minNode = None

        for node in n_map:
            # Determine which of the connected nodes have the lowest cost ...initializes to start_point
            if minNode == None:
                minNode = node
            elif data[node]['cost'] < data[minNode]['cost']:
                minNode = node

        # Loop connected nodes and adjust costs to each one
        for childNode, cost in n_map[minNode].items():

            path_cost = cost + data[minNode]['cost']

            if path_cost < data[childNode]['cost']:

                data[childNode]['cost'] = path_cost
                predecessor[childNode] = minNode

        n_map.pop(minNode)  # Remove the visited Node

    currentNode = end_point

    while currentNode != start_point:

        try:
            path.insert(0, currentNode)
            currentNode = predecessor[currentNode]
        except KeyError:
            print("Path not reachable")
            break

    if data[end_point]['cost'] != np.inf:   # If the endpoint is reachable
        return path
    else:
        return []


def bi_directional_sectors(current_map):

    for key, sector in current_map.items():  # loop Sctor objects in dictionary

        for connection, cost in sector.connected_sectors.items():

            current_map[connection].connected_sectors[key] = cost

    return current_map


def generate_map(total_sectors=100):

    map = {}

    for current_sector in range(1, total_sectors+1):

        map[current_sector] = Sector(current_sector)

    map = bi_directional_sectors(map)

    return map


if __name__ == "__main__":

    total_sectors = 1000
    map = generate_map(total_sectors)

    user = Player(500, 1_000_000)

    map[user.current_sector].load_sector()

    while True:

        player_input = input("Select Action:\t").lower()

        if player_input == "0":
            break
        else:
            user.check_input(player_input)
