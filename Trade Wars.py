import random
import numpy as np
from enum import Enum
import time
import collections

#import threading
#import socket

prompt_breaker = "============================================================================"

default_deployed = {'Limpets': {}, "Mines": {},
                    "Warp Disruptors": {}, "Fighters": {}}

default_undeployed = dict.fromkeys(default_deployed.keys(), 0)

default_undeployed.update(
    {"Photon Ammo": 0, "Planet Crackers": 0, "Planet Generators": 0})

default_cargo = {'Ore': [], "Organics": [],
                 "Equipment": [], 'Armor': [], "Batteries": []}


class Action(Enum):
    previous_menu = 0
    buy = 1
    sell = 2


class Ship:

    def __init__(self, total_cargo_holds, warp_cost, cargo, attached_limpets, useable_items,
                 model, current_sector, ship_name, cloak_enabled,
                 health, owner_in_ship, warp_drive_available, owner=None):
        self.total_cargo_holds = total_cargo_holds
        self.warp_cost = warp_cost            # How much it costs to warp between sectors
        self.cargo = cargo                    # Commodities or colonists
        self.attached_limpets = attached_limpets
        self.useable_items = useable_items    # Unused items
        self.model = model                    # Ship class name
        self.current_sector = current_sector
        self.ship_name = ship_name
        self.cloak_enabled = cloak_enabled
        self.health = health
        self.owner_in_ship = owner_in_ship
        self.owner = owner
        self.warp_drive_available = warp_drive_available
        self.destroyed = False

        initialized_sector = map_[self.current_sector].ships_in_sector

        if not self in initialized_sector:
            initialized_sector.append(self)

    def move_sectors(self, destination=None):

        start = self.current_sector

        print(f'Current Sector:\t{start}')

        # Prompt user for a valid destination or to exit the menu
        while True:

            if destination == None or not destination in range(1, game.total_sectors+1):

                try:
                    print("Press 0 to return to the previous menu")
                    end = int(
                        input("Enter target sector (1-{})> ".format(game.total_sectors)))
                    break
                except:
                    print("Please input a number.")
            else:
                end = destination
                break

        if end == 0:  # If destination sector isn't given, re-display the current sector
            self.ship_sector().load_sector(
                self, lessen_fighter_response=False, process_events=False)
            return

        elif end in range(1, game.total_sectors+1):

            if not end in self.ship_sector().connected_sectors:
                # More than 1 warp required to reach the destination
                sectors_to_load = BFS(start, end, map_)
            else:
                sectors_to_load = [end]

            print('Path: ' + " > ".join([str(element)
                                        for element in [self.current_sector] + sectors_to_load]))

            print(prompt_breaker)

            for sector in sectors_to_load:

                old_sector = self.ship_sector()

                # old_sector.connected_sectors[sector] > 0:
                if self.owner.turns_remaining-self.warp_cost > 0:

                    lessen_fighter_response = True if sector != end else False

                    time.sleep(.4)
                    self.owner.turns_remaining -= self.warp_cost

                    old_sector.ships_in_sector.remove(self)

                    self.current_sector = sector

                    new_sector = self.ship_sector()

                    new_sector.ships_in_sector.append(self)

                    new_sector.load_sector(
                        self.owner, lessen_fighter_response, process_events=True)

                else:
                    print("Not enough Fuel.")
                    break

        else:
            print("Input a valid number.")

    def holds_available(self):

        holds_used = sum([quantity[0]
                         for value in self.cargo.values() for quantity in value])

        return self.total_cargo_holds-holds_used

    def show_cargo(self):

        print("Current Cargo Manifest\n")

        for key, quantity in self.cargo.items():

            print(f"{key}: {quantity}")

        time.sleep(1)

        print("\n"+prompt_breaker)

    def return_cargo_quantity(self, item):
        return sum([quantity[0] for quantity in self.cargo[item]])

    def mine_interactions(self, mines):

        mine_damage = 250
        armor_mitigation = 250
        shield_mitigation = 1000

        mines_used = 1/8 * mines.quantity

        if mines_used == 0:
            mines_used = 1

        mines.edit_amount_in_sector(
            mines_used, attaching_limpet_to_hull=False)

        induced_damage = mines_used * mine_damage

        damage_mitigation = self.shields * shield_mitigation + \
            self.return_cargo_quantity(
                "Armor")*armor_mitigation

        damage_to_ship = induced_damage-damage_mitigation

        if damage_to_ship > 0:
            # Not all damage could be mitigated
            self.health -= damage_to_ship
            self.shields = 0
            self.cargo["Armor"].clear()
            # Test if ship was destroyed
            if self.health <= 0:
                self.ship_destroyed(mines.owner, True, False, False)

        else:
            # All damage mitigated
            damage_remaining = induced_damage

            if self.shields > 0:    # If the ship has shields

                shields_consumed = round(
                    damage_remaining / shield_mitigation, 2)

                if shields_consumed > self.shields:
                    damage_remaining -= (self.shields * shield_mitigation)
                    self.shields = 0
                else:
                    self.shields -= shields_consumed
                    damage_remaining = 0

            if damage_remaining > 0 and self.return_cargo_quantity("Armor") > 0:

                armor_consumed = damage_remaining // armor_mitigation
                self.cargo["Armor"] -= armor_consumed

    def limpet_interactions(self, limpets):

        new_limpet = Limpet(self, limpets.owner, True)

        limpets.edit_amount_in_sector(-1,
                                      attaching_limpet_to_hull=True)

        self.attached_limpets.append(new_limpet)

        limpets.owner.tracked_limpets.append(new_limpet)

    def ship_destroyed(self, destroyer, mines, fighters, sci_fi):

        self.ship_sector().ships_in_sector.remove(self)
        self.clear_limpets()

        if self.owner_in_ship:

            if self.model == "Escape Pod":
                self.owner.ship = None
                escape_pod_destroyed = True
                '''!    !   !   !   !'''
                # Deny turns for the rest of the day
            else:
                # Place user in an Escape Pod in a random sector

                escape_pod_warp = random.randint(1, total_sectors)

                self.owner.ship = create_new_ship(
                    0, self.owner, escape_pod_warp)

            if not escape_pod_destroyed:

                if mines:
                    score_transfer = self.owner.score * .10
                    transaction = self.owner.credits * .05
                elif fighters:
                    score_transfer = self.owner.score * .25
                    transaction = self.owner.credits * .10
                elif sci_fi:
                    score_transfer = self.owner.score * .29
                    transaction = 0

                destroyer.score += score_transfer
                self.owner.score -= score_transfer

                if transaction > 0:
                    destroyer.credits += transaction
                    self.owner.credits -= transaction

        self.destroyed = True

    def ship_sector(self):

        return map_[ship.current_sector]

    def clear_limpets(self):
        # Mainly to ensure that references to the limpet are removed and if not\
        # then it is inactive
        if len(self.attaached_limpets) > 0:
            for limpet in self.attached_limpets:
                limpet.active = False
            self.attached_limpets.clear()
            # for player in game.players.values:
            #   player.deployed["Limpets"].remove(limpet)


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

    def edit_amount_in_sector(self, quantity, attaching_limpet_to_hull):
        '''Edits quantity of deployable in the sector... deletes from sector and player log if less than 0'''

        if quantity > 0:
            self.quantity += quantity
            self.owner.ship.useable_items[self.type_] -= quantity
        else:
            self.quantity -= quantity

            if not attaching_limpet_to_hull:
                # If the owner of the item is retrieveing them from a sector
                self.owner.ship.useable_items[self.type_] += quantity

        if self.quantity <= 0:  # If the deployable no longer has any of itself in the sector

            self.deployed_sector().deployed_items.remove(self)

            del self.owner.deployed[self.type_][self.sector_num]

    def deployed_sector(self):
        '''Returns the object representing the sector the deployable is in.'''
        return map_[self.current_sector]


class Limpet:
    '''Attaches to ship hulls and reports positioning to owner.'''

    def __init__(self, tracked_ship, owner, active):
        self.tracked_ship = tracked_ship
        self.owner = owner
        self.active = active

    def current_location(self):

        if self.active:
            return self.tracked_ship.current_sector


class Player:

    def __init__(self, name, player_credits,
                 turns_remaining, score, deployed, corporation, tracked_limpets, ship):

        self.name = name
        self.corporation = corporation
        #self.current_sector = current_sector
        self.credits = player_credits
        self.turns_remaining = turns_remaining
        self.score = score
        self.ship = ship

        # Dictionary for where deployables placed by player are in the world
        self.deployed = deployed
        self.tracked_limpets = tracked_limpets

    def use_item(self, item, quantity, mode=None, changing_quantity=False, changing_properties=False):
        '''Use,edit or add a useble item to the current sector.'''
        target_sector = self.player_sector()

        ship_sector = self.ship.current_sector

        if item in ["Limpets", "Mines", "Fighters", "Warp Disruptors"]:
            # Mines,Limpets,Warp disruptors,Fighters

            # Check if player already has deployables of that type in the sector
            if self.ship.current_sector in self.deployed[item]:
                # You have to be in the sector to edit deployables
                deployed_item = self.deployed[item][ship_sector]

                if changing_quantity:

                    deployed_item.edit_amount_in_sector(quantity, False)

                elif changing_properties:
                    # Used for editing deployed fighter status
                    pass
            else:
                placed_deployable = Deployable(
                    self, item, ship_sector, quantity, mode)

                target_sector.place_deployable_in_sector(placed_deployable)

                self.deployed[item][ship_sector] = placed_deployable

        elif item in ["Planet Crackers", "Photon Ammo"]:

            if item == "Planet Crackers":
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
        elif item == "Planet Generators":
            target_sector.create_planet(self)

        if not changing_quantity:  # If not modifying the quantity of an already existing deployable
            self.ship.useable_items[item] -= quantity

    def add_to_avoid_list(self, new_sector):

        pass

    def check_input(self, action):
        '''Function is called whenever a player creates a keyboard input while sitting in a sector outside of a planet or port'''
        print(prompt_breaker)

        if action == "":  # User pressed enter
            pass

        elif action[0] == 'm':
            # Player wants to move sectors
            if len(action) > 1:
                # Possibly more input after the letter m
                dest = action[1:].replace(" ", "")
                if dest.isdigit():
                    dest = int(dest)
                else:
                    dest = None
            else:

                nearby_sectors = " | ".join(
                    [str(element) for element in list(self.player_sector().connected_sectors.keys())])

                print('[Nearby Warps] : ' + nearby_sectors + '\n')

                dest = None

            self.ship.move_sectors(dest)

        elif action[0] == "c":
            # User wants to view ship cargo
            self.ship.show_cargo()
            self.player_sector().load_sector(
                self, lessen_fighter_response=False, process_events=False)
        elif action[0] == "u":
            # User wants to view items available for use
            self.item_selection()

        elif action.isdigit():  # Used for entering Ports or Planets

            action = int(action)

            try:
                sector_obj = self.player_sector()
                sector_obj.ports[action].enter_port(self)
                sector_obj.load_sector(
                    self, lessen_fighter_response=True, process_events=False)
            except KeyError:
                pass

    def item_selection(self):

        count = 1

        ship_items = self.ship.useable_items

        for item, quantity in ship_items.items():
            tabs = "\t\t" if len(item) <= 10 else "\t"
            print(f"({count})  {item}{tabs}Available:\t{quantity}")
            count += 1
        else:
            print("\n(0)    Exit\n")

        while True:
            try:
                selection = int(input("Select an option from the list: \t"))
                if selection in range(count+1):
                    break
            except ValueError:
                print("Input a number.")

        if selection == Action.previous_menu.value:
            return
        else:

            # Get the key corresponding to the user selection
            item = list(ship_items.keys())[selection-1]

            available_quantity = ship_items[item]

            if available_quantity > 0:

                if item in ["Limpets", "Mines", "Fighters", "Warp Disruptors"]:
                    quantity = int(
                        input(f"How many {item} do you want to deploy (0-{available_quantity})?\t"))

                    if quantity > 0:

                        if item == "Fighters":
                            # Prompt player for deployment mode
                            pass

                        self.use_item(item, quantity)

                else:
                    quantity = 1
                    # now check if planet creator,destroyer,photon cannon
                    self.use_item(item, quantity)
            else:
                print(f"\nNo {item} were found on ship.\n")
                time.sleep(1)

        self.player_sector().load_sector(self, True, False)

    def player_sector(self):
        return map_[self.ship.current_sector]

    def assign_ship(self, ship):
        ship.owner = self
        self.ship = ship


class Planet:

    def __init__(self, owner, sector, planet_type, name, fighters, population, shields, inventory, citadel):

        self.sector = sector

        self.owner = owner
        self.corporation = owner.corporation

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

    def destroy_planet(self):
        pass

    def land_on_planet(self):
        pass


class Sector:

    def __init__(self, sector_number, ports_in_sector=None, connected_sectors=None, deployed_items=[], debris_percent=0, ships_in_sector=[], game_sectors_total=1_000):

        self.sector = sector_number
        # List of items players have placed in the sector
        self.deployed_items = deployed_items.copy()
        self.debirs_percent = debris_percent
        self.ships_in_sector = ships_in_sector.copy()

        if ports_in_sector == None and sector_number != 1:
            self.ports = self.generate_ports()
        elif sector_number == 1:
            self.ports = {}
        else:
            self.ports = ports_in_sector

        if connected_sectors == None:
            self.connected_sectors = self.generate_connecting_sectors(
                game_sectors_total)
        else:
            self.connected_sectors = connected_sectors

    def place_deployable_in_sector(self, deployable):

        # Deployable can either be of the Deployable or Planet class
        self.deployed_items.append(deployable)

    def load_sector(self, player, lessen_fighter_response, process_events):

        # load events will be used for hazard / deployable interaction

        nearby_sectors = " - ".join(
            [str(element) for element in list(self.connected_sectors.keys())])

        print(
            f'\n[Current Sector]: {self.sector}\t\t\t[Fuel remaining]: {player.turns_remaining:,}\n ')

        planets = self.planets_in_sector()

        interface_num = 1

        if len(planets) > 0:

            print("*************************************")
            print("              Planets                \n")

            for planet in planets:
                print(f"({interface_num})\t\t{planet.name}")
                interface_num += 1
            print("\n*************************************\n")

        if self.sector == 1:
            pass
            # Load TERRA
        elif len(self.ports) > 0:

            # Print the ports in the sector
            for num, port in enumerate(self.ports.values()):
                print(f'({num+interface_num}) {port.name}')

        print(
            f'\n[Nearby Warps] : ' + nearby_sectors + '\n')

        ships = [
            ship.ship_name for ship in self.ships_in_sector if not ship.cloak_enabled]

        if len(ships) > 0:
            print(str(ships)+"\n")

        if process_events:
            # Deal with deployables and enviromental hazards
            self.sector_events(player, lessen_fighter_response)

        print(prompt_breaker)

    def load_terra(self):
        pass

    def generate_connecting_sectors(self, total_sectors):

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

    def create_planet(self, planet_owner, planet=None):

        if planet == None:

            planet_inventory = {'Ore': 0, "Organics": 0,
                                "Equipment": 0, 'Armor': 0, "Batteries": 0}
            planet_population = planet_inventory.copy()
            fighters = 0
            planetary_shields = 0
            planet_type = random.randint(1, 9)
            citadel = None

            new_planet = Planet(planet_owner, self.sector, planet_type, input("Enter planet name:\t"),
                                fighters, planet_population, planetary_shields, planet_inventory, citadel)

            self.place_deployable_in_sector(new_planet)

            self.load_sector(planet_owner, False, False)

        else:
            self.place_deployable_in_sector(planet)

    def planets_in_sector(self):

        planet_list = []
        for obj in self.deployed_items:
            if isinstance(obj, Planet):
                planet_list.append(obj)

        return planet_list

    def sector_events(self, victim, mitigate_fighters):

        for deployable in self.deployed_items:

            friendly = True if victim is deployable.owner\
                or (deployable.owner.corporation == victim.corporation
                    and deployable.owner.corporation != None
                    and victim.corporation != None)\
                else False

            if not friendly:

                if deployable.type == "Limpets":

                    victim.ship.limpet_interaction(deployable)

                elif deployable.type == "Mines":

                    victim.ship.mine_interactions(deployable)

                elif deployable.type == "Warp Disruptors":

                    # Increase turn count cost
                    pass

                elif deployable.type == "Fighters":
                    if mitigate_fighters:
                        pass
                    else:
                        pass


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
                    [x[0] for x in player.ship.cargo[key]])

                if item_quantity_in_holds > 0:
                    avg_price = np.average([x[1]
                                            for x in player.ship.cargo[key]])
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

            items_on_ship = player.ship.holds_available() != player.ship.total_cargo_holds

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

                    available_units = min(player.ship.holds_available(
                    ), player_can_afford, self.inventory[commodity]['Quantity'])

                else:
                    item_quantity_in_holds = sum(
                        [x[0] for x in player.ship.cargo[commodity]])

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

            # Edit the below line so users can sell what ever amount they want
            player.ship.cargo[item].clear()

            self.credits -= transaction_cost
            player.credits += transaction_cost
            player.score += 1000

    def buy_from_port(self, player_buying_quantity, item, player):

        commodity = self.inventory[item]

        transaction_cost = player_buying_quantity * commodity['Price']

        if player_buying_quantity <= commodity['Quantity'] and transaction_cost <= player.credits:

            # Reduce port quantity WTB
            commodity["Quantity"] -= player_buying_quantity

            player.ship.cargo[item].append(
                (player_buying_quantity, commodity['Price']))

            self.credits += transaction_cost
            player.credits -= transaction_cost
            player.score += 1000

    def steal_from_port(self, quantity, item):
        pass

    def restock(self):
        self.credits += 100_000
        self.fuel_ore += 10_000
        self.organics += 10_000
        self.armor += 10_000
        self.batteries += 10_000
        self.credits += 300_000


class Game:

    def __init__(self, chart, players, deployables):

        self.players = players
        self.map_ = chart
        self.total_sectors = len(chart)

    def return_player(self, player_name):
        self.players[player_name]


def join_all_sectors(total_sectors, current_map):
    '''
    Use Depth First Search algorithm to ensure all sectors are connected
    '''
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


def dijkstra_path(start_point, end_point, current_map):
    '''
    Dijkstra's algorithm used to find shortest fuel cost path 
    '''

    data = {key: np.inf for key in map_}

    data[start_point] = 0

    predecessor = {}

    n_map = {sector: current_map[sector].connected_sectors.copy()
             for sector in map_}

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

    current_map = {}

    for current_sector in range(1, total_sectors+1):
        # Each sector originally connects to 2 to 4 other sectors
        current_map[current_sector] = Sector(
            current_sector, game_sectors_total=total_sectors)

    # Ensure that every sector is reachable
    current_map = join_all_sectors(total_sectors, current_map)

    return current_map


def create_new_ship(new_ship_class, owner, spawn_sector):

    attached_limpets = []

    cargo = default_cargo.copy()
    ship_name = "Unknown Vessel"
    items = default_undeployed.copy()

    if new_ship_class == 0:   # Escape Pod for when ships are destroyed
        total_holds = 10
        warp_cost = 0
        ship_health = 500
        model = "Escape Pod"
        warp_drive_available = False

    elif new_ship_class == 1:  # Default starting ship
        total_holds = 1_000
        warp_cost = 3
        ship_health = 50_000
        model = "Class I"
        warp_drive_available = False

    return Ship(total_holds, warp_cost, cargo, attached_limpets, items, model,
                spawn_sector, ship_name, False, ship_health, True,  warp_drive_available, owner)


def default_player_properties(sector_total):

    deployed_items = default_deployed.copy()

    corporation = None

    tracked_limpets = []

    turns_remaining, score, credits, starting_sector = 10_000, 0, 20_000, random.randint(
        1, sector_total)

    return deployed_items, corporation,  turns_remaining, score, credits, starting_sector, tracked_limpets


if __name__ == "__main__":

    player_name = "Reshui"
    total_sectors = 1_000

    map_ = generate_map(total_sectors)

    deployed_items, corporation, turns_remaining, score, credits, starting_sector, tracked_limpets \
        = default_player_properties(total_sectors)

    ship = create_new_ship(new_ship_class=1, owner=None,
                           spawn_sector=starting_sector)
    # Ideally these should all be retrieved from a databse of some sort
    user = Player(player_name,  credits,
                  turns_remaining, score, deployed_items, corporation,  tracked_limpets, None)

    # Assigns the ship to the owner AND designates the player as the owner of the ship
    user.assign_ship(ship)

    game_deployables = {}

    game = Game(map_, {player_name: user}, game_deployables)

    user.player_sector().load_sector(
        user, lessen_fighter_response=False, process_events=False)

    while True:

        player_input = input("Select Action:\t").lower()

        if player_input == "0":
            break
        else:
            user.check_input(player_input)
