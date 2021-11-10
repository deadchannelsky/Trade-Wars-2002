import random
import numpy as np
from enum import Enum
import time
import collections
import copy
#import threading
#import socket

prompt_breaker = "============================================================================"


class Action(Enum):
    previous_menu = 0
    buy = 1
    sell = 2


class DeployableType(Enum):
    limpets = 1
    mines = 2
    warp_disruptor = 5
    fighter = 6

    planet_cracker = 3
    planet_creator = 4
    photon_cannon = 7


class Deployable:
    '''This class is for items that can be placed by the player and will persist until interacted withh'''
    #  "Limpets"
    #  "Mines"
    #  "Warp Disruptors"
    #  "Fighters"

    def __init__(self, owner, type_, sector_num, quantity,  mode=None):
        self.sector_num = sector_num
        self.type_ = type_
        self.quantity = quantity
        self.owner = owner

        self.mode = mode                              # Used for fighter state


class Player:

    def __init__(self, name, current_sector, player_credits, cargo_holds,
                 turns_remaining, score, undeployed, cargo, deployed, corporation):

        self.username = name
        self.current_sector = current_sector
        self.credits = player_credits
        self.cargo_holds = cargo_holds
        self.fuel = turns_remaining
        self.score = score
        self.cargo = cargo
        self.deployed = deployed
        self.undeployed = undeployed
        self.corporation = corporation

    def use_item(self, item_num, quantity, mode=None):

        target_sector = map[self.current_sector]

        if item_num in [1, 2, 5, 6]:
            # Mines,Limpets,Warp disruptors,Fighters
            placed_deployable = Deployable(
                self, item_num, self.current_sector, quantity, mode)

            target_sector.place_deployable_in_sector(placed_deployable)

        elif item_num in [3, 7]:

            if item_num == 3:
                #   Planet Cracker
                available_planets = target_sector.planets_in_sector()

                if len(available_planets) > 0:
                    # Print out the names of each planet and prompt user for selection
                    # Destroy planet if no defenses
                    pass
            else:
                # Photon Cannon
                # Launches turn denial weapon
                # Disables Quasar cannons temporarily for 20 seconds
                pass
        else:
            # Planet creator
            target_sector.create_planet(self)

    def holds_available(self):

        holds_used = sum([quantity[0]
                         for value in self.cargo.values() for quantity in value])

        return self.cargo_holds-holds_used

    def avoid_list(self, avoided_sectors):

        return avoided_sectors

    def check_input(self, action):

        print(prompt_breaker)

        if action == "":
            pass

        elif action[0] == 'm':

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

        elif action[0] == "c":

            print("Current Cargo Manifest")

            for key, quantity in self.cargo.items():
                print(f"{key}: {quantity}")
            time.sleep(.5)
            print(prompt_breaker)
            map[self.current_sector].load_sector(
                self, currently_warping=False, process_events=False)

        elif action.isdigit():  # Used for entering Ports or Planets

            action = int(action)

            try:
                sector_obj = map[self.current_sector]
                sector_obj.ports[action].enter_port(self)
                sector_obj.load_sector(
                    self, currently_warping=True, process_events=True)
            except KeyError:
                pass

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
            # Replace this with re-display sector !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            map[self.current_sector].load_sector(
                self, currently_warping=False, process_events=False)
            return

        elif 1 <= end <= total_sectors:

            if not end in map[self.current_sector].connected_sectors:

                sectors_to_load = BFS(start, end, map)
               # sectors_to_load = dijkstra_path(start, end, map)
            else:
                sectors_to_load = [end]

            #print('Lowest Cost: ' + str(data[end_point]['cost']))

            print('Path: ' + " > ".join([str(element)
                                        for element in [self.current_sector] + sectors_to_load]))

            print(prompt_breaker)

            for sector in sectors_to_load:

                if self.fuel-map[self.current_sector].connected_sectors[sector] > 0:

                    time.sleep(.4)
                   # Subtract the cost to travel to the sector

                    self.fuel -= \
                        map[self.current_sector].connected_sectors[sector]

                    self.current_sector = sector

                    map[sector].load_sector(
                        self, currently_warping=True, process_events=True)

                else:
                    print("Not enough Fuel.")
                    break

        else:
            print("Input a valid number.")


class Planet:

    def __init__(self, owner, sector, planet_type, name, fighters, population, shields, inventory, citadel):

        self.sector = sector
        self.owner = owner

        # Dictionary listing total population and their distribution for each commodity
        self.population = population
        self.planet_type = planet_type
        self.name = name
        self.fighters = fighters
        self.shields = shields
        # Dictionary listing how much of each commodity is on the planet
        self.inventory = inventory
        self.citadel = citadel

    def rename(self, new_name):
        self.name = new_name


class Sector:

    def __init__(self, sector_number, ports_in_sector=None, connected_sectors=None, deployed_items=[], debris_percent=0):

        self.sector = sector_number
        self.deployed_items = deployed_items
        self.debirs_percent = debris_percent

        if ports_in_sector == None and sector_number != 1:
            self.ports = self.generate_ports()
        elif sector_number == 1:
            self.ports = {}
        else:
            self.ports = ports_in_sector

        if connected_sectors == None:
            self.connected_sectors = self.generate_connecting_sectors()
        else:
            self.connected_sectors = connected_sectors

    def place_deployable_in_sector(self, deployable):

        # Deployable can either be of the Deployable or Planet class
        self.deployed_items.append(deployable)

    def load_sector(self, player, currently_warping, process_events):

        # load events will be used for hazard / deployable interaction

        nearby_sectors = " - ".join(
            [str(element) for element in list(map[self.sector].connected_sectors.keys())])

        print(
            f'\n[Current Sector]: {self.sector}\t\t\t[Fuel remaining]: {player.fuel:,}\n ')

        if self.sector == 1:
            pass
            # Load TERRA
        elif len(self.ports) > 0:

            # Print the ports in the sector
            for num, port in enumerate(self.ports.values()):
                print(f'({num+1}) {port.name}')

        print(
            f'\n[Nearby Warps] : ' + nearby_sectors + '\n')

        print(prompt_breaker)

    def load_terra(self):
        pass

    def generate_connecting_sectors(self):

        total_connecting_sectors = random.randrange(2, 4)

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

        ports_in_system = random.randint(1, 2)

        if ports_in_system > 0:

            for port_number in range(1, ports_in_system+1):

                sector_ports[port_number] = TradePort(
                    self.sector, port_number)
        return sector_ports

    def create_planet(self, owner, planet=None):

        if planet == None:

            planet_inventory = {'Ore': 0, "Organics": 0,
                                "Equipment": 0, 'Armor': 0, "Batteries": 0}
            planet_population = planet_inventory.copy()
            fighters = 0
            planetary_shields = 0
            planet_type = random.randint(1, 9)
            citadel = None

            new_planet = Planet(self.sector, owner, planet_type, input("Enter planet name:\t"),
                                fighters, planet_population, planetary_shields, planet_inventory, citadel)

            self.place_deployable_in_sector(new_planet)
        else:
            self.place_deployable_in_sector(planet)

    def planets_in_sector(self):

        planet_list = []
        for obj in self.deployed_items:
            if isinstance(obj, Planet):
                planet_list.append(obj)

        return planet_list


class TradePort:

    def __init__(self, sector, port_number):
        self.sector = sector
        self.name = 'Trading Port {} ~ {}'.format(sector, port_number)
        # Fuel for ship/Planetary shields
        self.credits = random.randint(20_510_000, 90_700_000)
        self.inventory = self.generate_info(False)

    def generate_info(self, update_only_prices=False):

        if not update_only_prices:
            info = {}

            for field in ["Ore", "Organics", "Armor", "Batteries", "Equipment"]:
                info[field] = {}
        else:
            info = self.inventory

        quantities = [(30_000, 150_000), (40_000, 200_000),
                      (60_000, 100_000), (10_000, 45_000), (5_000, 10_000)]

        if not update_only_prices:
            self.price_random = ((1000, random.randint(200, 300)), (2000, random.randint(100, 200)),
                                 (500, random.randint(978, 1500)), (15000, random.randint(9, 12)), (800, random.randint(3000, 4000)))

        for item, amount, price in zip(info.values(), quantities, self.price_random):

            if not update_only_prices:
                item['Quantity'] = random.randint(*amount)
                item['Status'] = random.choice(("Buying", "Selling"))

            if item['Status'] == "Selling":
                # Higher prices with smaller WTS
                item["Price"] = round(price[1] - item['Quantity']/price[0], 3)
            else:
                # Lower Prices with smaller WTB
                item["Price"] = round(item['Quantity']/price[0] + price[1], 3)

        return info

    def enter_port(self, player):

        while True:
            # Update Prices if needed
            self.inventory = self.generate_info(True)

            # Print Quantities of items and there Buy/Sell price
            print(
                f"\nPort Funds: {self.credits:,}\nYour Balance: {player.credits:,}")

            print(prompt_breaker + '\n' + self.name + '\n')

            for item, cargo in self.inventory.items():
                # Print the ports current inventory and corresponding
                # Prices to the screen

                if len(item) <= 5:
                    tabs = '\t'
                else:
                    tabs = ""

                printed_string = f'{item}{tabs}'

                print(
                    f'{printed_string}\t{cargo["Status"]}\t\t{cargo["Quantity"]:,}\t\t    $ {cargo["Price"]:,}')

            print(prompt_breaker)

            while True:
                try:
                    user_selection = int(
                        input("Select an option: (1) Buy from Port | (2) Sell to Port | (0) Exit port:   "))
                    if user_selection in range(0, 3):
                        break
                except:
                    pass
                print("Input a number 0-2 ")

            print(prompt_breaker + "\n")

            if user_selection == Action.sell.value:

                try:
                    item, quantity = self.buy_sell_prompt(False, player)
                except:
                    # If the user presses 0 to cancel their selection
                    continue

                self.sell_to_port(quantity, item, player)

            elif user_selection == Action.buy.value:

                try:
                    item, quantity = self.buy_sell_prompt(True, player)
                except:
                    # If the user presses 0 to cancel their selection
                    continue

                self.buy_from_port(quantity, item, player)

            elif user_selection == Action.previous_menu.value:

                break

            else:
                print("Invalid selection")

            print(prompt_breaker)

    def buy_sell_prompt(self, buying, player):

        sell_or_buy = "buy" if buying == True else "sell"

        available_for_purchase = []

        for key in self.inventory:

            if buying and self.inventory[key]["Status"] == "Selling" or not buying and self.inventory[key]["Status"] == "Buying":

                tabs = "\t\t"

                if len(key) <= 3:
                    tabs += '\t'

                item_quantity_in_holds = sum(
                    [x[0] for x in player.cargo[key]])

                if item_quantity_in_holds > 0:
                    avg_price = np.average([x[1]
                                            for x in player.cargo[key]])
                else:
                    avg_price = 0

                if item_quantity_in_holds == 0 and not buying:
                    continue
                elif item_quantity_in_holds > 0:
                    average_bought_string = f'\tAverage Price: {avg_price}'
                else:
                    average_bought_string = ""

                if len(str(self.inventory[key]["Price"])) == 8:
                    tabs2 = "\t"
                else:
                    tabs2 = "\t\t"

                available_for_purchase.append(key)

                print(
                    f'{len(available_for_purchase)} - {key}{tabs}{self.inventory[key]["Price"]}{tabs2}On ship: {item_quantity_in_holds:,}\t{average_bought_string}')

        if len(available_for_purchase) == 0:  # Check if trades aren't possible

            items_on_ship = player.holds_available() != player.cargo_holds

            if not buying:

                if items_on_ship:
                    print(
                        "Nothing in your inventory is available to be sold at this time.")
                else:
                    print(
                        f"You don't have any cargo on your ship.\n{prompt_breaker}")
            else:
                if items_on_ship:
                    print("Nothing available for purchase at this time.")

            time.sleep(1)

            return

        else:

            print("\n0 - Exit Menu\n")
            print(prompt_breaker)

            while True:  # Prompt player for which item they would like to buy or sell
                try:
                    selection = int(
                        input(f"What would you like to {sell_or_buy}?\t"))

                    if selection in range(len(available_for_purchase)+1):
                        break
                    else:
                        print(
                            f"\nInput a number 0 - {len(available_for_purchase)}\n")
                except ValueError:
                    print("Input a number")

            if selection == Action.previous_menu.value:  # Equal to 0
                return
            else:

                print(prompt_breaker)
                # Rerieve the name of the selected commodity
                commodity = available_for_purchase[selection-1]

                commodity_price = self.inventory[commodity]['Price']

                if buying:

                    player_can_afford = int(player.credits/commodity_price)

                    available_units = min(player.holds_available(
                    ), player_can_afford, self.inventory[commodity]['Quantity'])

                else:
                    item_quantity_in_holds = sum(
                        [x[0] for x in player.cargo[commodity]])

                    port_can_afford = int(self.credits/commodity_price)
                    available_units = min(
                        item_quantity_in_holds, port_can_afford)

                while True:  # Prompt user for how much they'd like to trade
                    # Show them how many credits they will gain or lose

                    print(
                        f'{commodity} units available for purchase: {available_units:,}')

                    while True:
                        try:
                            quantity = int(
                                input(f"\nHow many units would you like to {sell_or_buy}? \t"))

                            if quantity <= 0:
                                return
                            elif quantity > available_units:
                                print(
                                    f"\nInput a quantity between 0 and {available_units}")
                            else:
                                break
                        except ValueError:
                            print("\nInput a number\n")

                    transaction_cost = commodity_price * quantity

                    sign = "-" if buying == True else "+"

                    print(
                        f'\nCurrent Balance: {player.credits:,} || New Balance: {player.credits + (-1* transaction_cost if buying else transaction_cost) :,} || Change: {sign} {transaction_cost:,}\n')

                    selection = input(
                        "Press [Enter] to confirm or [0] to cancel transaction.")

                    if selection == "":  # If user has pressed Enter

                        if quantity in range(0, available_units+1):

                            if quantity == Action.previous_menu.value:
                                return
                            else:
                                break   # Transaction details have been confirmed
                        else:
                            print(
                                "\nPlease input a number less than or equal to the number of holds available.\n")
                    else:
                        return  # User wasnts to cancel transaction
                return commodity, quantity

    def sell_to_port(self, player_selling_quantity, item, player):

        commodity = self.inventory[item]

        transaction_cost = player_selling_quantity * commodity['Price']

        if transaction_cost <= self.credits:

            # Port is no longer Selling that amount
            commodity["Quantity"] -= player_selling_quantity

            player.cargo[item].clear()
            #player.cargo[item].append((player_selling_quantity, commodity["Price"]))

            self.credits -= transaction_cost
            player.credits += transaction_cost

    def buy_from_port(self, player_buying_quantity, item, player):

        commodity = self.inventory[item]

        transaction_cost = player_buying_quantity * commodity['Price']

        if player_buying_quantity <= commodity['Quantity'] and transaction_cost <= player.credits:

            # Reduce port quantity WTB
            commodity["Quantity"] -= player_buying_quantity

            player.cargo[item].append(
                (player_buying_quantity, commodity['Price']))

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


def join_all_sectors(current_map, total_sectors):
    '''
    Use Depth First Search algorithm to ensure all sectors are connected
    '''
    #current_map = bi_directional_sectors(current_map)

    map_partitions = {}
    visited = set()

    for root_sector in current_map:

        if not root_sector in visited:

            visited.add(root_sector)
            stack = [root_sector]
            section = stack.copy()

            # Depth First Search Algorithm to find sectors that are reachable from the root sector
            while stack:
                # While the stack isn't empty
                queried_sector = stack.pop()  # Retrieve the most recently added item

                for connected_sector in current_map[queried_sector].connected_sectors:

                    if not connected_sector in visited:

                        visited.add(connected_sector)
                        stack.append(connected_sector)
                        section.append(connected_sector)

            map_partitions[len(map_partitions)] = section

    # Sectors aren't guaranteed to be loopable [A<>B<>C<>A]
    # At minimum connected sectors are [A>B>C]

    # Sections that aren't reachable from sector 1 may have one or more one way connections \
    # into the section containing sector 1

    if len(map_partitions) > 1:
        # Return key for the largest section of the map
        largest_section = sorted(
            map_partitions, key=lambda x: len(map_partitions[x]))[-1]

        for key, section in map_partitions.items():

            if key != largest_section:
                # May change to create tunnels depending on the number of disjoint sectors
                # Choose a random sector to link to from the primary map
                entry_sector = random.choice(
                    map_partitions[largest_section])
                linked_sector = random.choice(section)

                current_map[entry_sector].connected_sectors[linked_sector] = 1

    # Make all sectors bi-directional
    for key, sector in current_map.items():

        for connection, cost in sector.connected_sectors.items():

            current_map[connection].connected_sectors[key] = cost

    return current_map


def BFS(start, end, current_map):
    '''
    Use Breadth First Search to find shortest path for when travel cost between nodes are the same
    Optimal to use this with previous clause if the number of sectors is large
    '''
    queue = collections.deque([start])
    visited = set()
    pred = {}
    target_found = False

    while queue and not target_found:
        node = queue.popleft()  # FIFO
        visited.add(node)
        for child_node in current_map[node].connected_sectors:
            # If child node is in visited then a node closer to the start is already connected
            if not child_node in visited:
                pred[child_node] = node
                if child_node == end:
                    target_found = True
                    break
                else:
                    queue.append(child_node)

    child_node = end

    path = collections.deque([])

    try:
        while child_node != start:
            path.appendleft(child_node)
            child_node = pred[child_node]
    except KeyError:
        return []

    return list(path)


def dijkstra_path(start_point, end_point, map):
    '''
    Dijkstra's algorithm used to find shortest fuel cost path 
    '''

    data = {key: np.inf for key in map}

    data[start_point] = 0

    predecessor = {}

    n_map = {sector: map[sector].connected_sectors.copy() for sector in map}

    while n_map:  # While there are still nodes to visit

        minNode = None

        for node in n_map:
            # Determine which of the nodes have the lowest path cost ... initializes to start_point
            if minNode == None:
                minNode = node
            elif data[node] < data[minNode]:
                minNode = node

        # Loop connected nodes and adjust costs to each one
        for childNode, cost in n_map[minNode].items():

            # Cost to get to the parent node + cost to get to the child
            path_cost = data[minNode] + cost

            # If a more optimal path is found or child is tested for the first time
            if path_cost < data[childNode]:

                data[childNode] = path_cost
                predecessor[childNode] = minNode

        n_map.pop(minNode)  # Remove the visited Node

    currentNode = end_point
    path = collections.deque([])

    while currentNode != start_point:
        try:
            path.appendleft(currentNode)
            currentNode = predecessor[currentNode]
        except KeyError:
            print("Path not reachable")
            break

    if data[end_point] != np.inf:   # If the endpoint is reachable
        return list(path)
    else:
        return []


def generate_map(total_sectors=100):

    map = {}

    for current_sector in range(1, total_sectors+1):

        # Create Sector objects
        # Each sector originally connects to 2 to 4 other sectors
        map[current_sector] = Sector(current_sector)

    # Ensure that every sector is reachable
    map = join_all_sectors(map, total_sectors)
    # Enable Bi-directional sector travel unil further updates
    return map


if __name__ == "__main__":

    total_sectors = 10_000

    map = generate_map(total_sectors)

    deployed_items = {'Limpets': {}, "Mines": {},
                      "Warp Disruptors": {}, "Fighters": {}}

    undeployed = dict.fromkeys(deployed_items.keys(), 0)
    undeployed.update(
        {"Photon Ammo": 0, "Planet Crackers": 0, "Planet Generators": 0})

    cargo = {'Ore': [], "Organics": [],
             "Equipment": [], 'Armor': [], "Batteries": []}

    corporation = None

    turns_remaining, score, total_holds, credits, starting_sector = 10_000, 0, 3_000, 20_000, random.randint(
        1, total_sectors)

    # Ideally these should be retrieved from a databse of some sort
    user = Player("Reshui", starting_sector, credits, total_holds,
                  turns_remaining, score, undeployed, cargo, deployed_items, corporation)

    map[user.current_sector].load_sector(
        user, currently_warping=False, process_events=True)

    while True:

        player_input = input("Select Action:\t").lower()

        if player_input == "0":
            break
        else:
            user.check_input(player_input)
