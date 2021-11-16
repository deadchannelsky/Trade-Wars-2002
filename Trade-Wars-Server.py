import random
import numpy as np
from enum import Enum
import time
import collections
import pandas as pd
import heapq
import threading
import socket

prompt_breaker = "=" * 96

default_deployed = {'Limpets': {}, "Mines": {},
                    "Warp Disruptors": {}, "Fighters": {}}

default_inventory_quantity = 1

default_undeployed = dict.fromkeys(
    default_deployed, default_inventory_quantity)

for utility in ["Photon Ammo", "Planet Crackers", "Planet Generators", "Cloaking Device", "Density Scanners"]:
    default_undeployed[utility] = default_inventory_quantity

default_cargo = {'Ore': [], "Organics": [],
                 "Equipment": [], 'Armor': [], "Batteries": []}

FORMAT = "utf-8"
HEADER = 64
DISCONNECT_MESSAGE = "!DISCONNECT"
PROMPT_INPUT = "!INPUT"


class Action(Enum):
    previous_menu = 0
    buy = 1
    sell = 2


class FighterModes(Enum):
    offensive = 1
    defensive = 2
    taxing = 3
    disabled = 4


class LocalNetwork:

    def __init__(self):
        self.port = 5050
        self.server_ip = socket.gethostbyname(socket.gethostname())
        self.addr = (self.server_ip, self.port)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(self.addr)
        self.connected_clients = []


class Ship:

    def __init__(self, total_cargo_holds, warp_cost, cargo, attached_limpets, useable_items,
                 model, current_sector, ship_name, cloak_enabled,
                 health, owner_in_ship, warp_drive_available, shields, owner=None):

        self.total_cargo_holds = total_cargo_holds
        self.warp_cost = warp_cost            # How much it costs to warp between sectors
        self.cargo = cargo                    # Commodities or colonists
        self.attached_limpets = attached_limpets
        self.useable_items = useable_items    # Unused items
        self.model = model                    # Ship class name
        self.current_sector = current_sector  # INT for the current sector
        self.ship_name = ship_name
        # Hides user from visual scans but not from density scans
        self.cloak_enabled = cloak_enabled
        self.health = health
        self.owner_in_ship = owner_in_ship    # Pilots can own multiple ships
        self.owner = owner
        # Allow Pilots to warp between sectors at a reduced turn rate if they have a feighter stationed there
        self.warp_drive_available = warp_drive_available
        self.destroyed = False
        self.shields = shields

        initialized_sector = game.chart[self.current_sector].ships_in_sector

        if not self in initialized_sector:
            initialized_sector.append(self)

    def traverse_map(self, end=None):
        '''Ship traverses map when given a destination. Loads each sector along the way
        '''
        # Determine if there is non-friendly interdictor effect active in the sector
        # Uncoded

        conn = self.owner.connection
        start = self.current_sector

        message_client(conn, f'Current Sector:\t{start}')

        # Prompt user for a valid destination or to exit the menu
        if end == None or end not in range(game.total_sectors+1):

            prompt = f"Press 0 to return to the previous menu\nEnter target sector (1-{game.total_sectors})> "
            end = get_input(prompt, range(
                game.total_sectors+1), True, False, conn)

        if end == 0:  # If destination sector isn't given, re-display the current sector
            self.ship_sector().load_sector(
                self.owner, lessen_fighter_response=False, process_events=False)
            return

        elif end in range(1, game.total_sectors+1):

            # If more than 1 warp required to reach the destination use BFS
            if not end in self.ship_sector().connected_sectors:

                sectors_to_load = self.breadth_first_search(
                    start, end, game.chart)
                #shortest_fuel_path = self.dijkstra_path(start, end, game.chart)

                if not sectors_to_load:
                    message_client(conn, "Sector isn't reachabele.")
                    return
            else:
                sectors_to_load = [end]

            displayed_path = [str(element) for element in [
                self.current_sector] + sectors_to_load]
            plotted_path = " > ".join(displayed_path)

            message_client(
                conn, f'Path: {plotted_path}\n{prompt_breaker}')

            for sector in sectors_to_load:

                if self.owner.turns_remaining-self.warp_cost > 0:
                    lessen_fighter_response = True if sector != end else False

                    self.change_sector(sector, lessen_fighter_response)
                    self.owner.turns_remaining -= self.warp_cost

                else:
                    message_client(
                        conn, "You don't have enough turns remaining to complete this warp.")
                    break

    def holds_available(self):
        '''Returns the number of unused cargo holds on the ship'''
        holds_used = sum([quantity[0]
                         for value in self.cargo.values() for quantity in value])

        return self.total_cargo_holds-holds_used

    def show_cargo(self):
        '''Prints a pandas DataFrame representing the ship's cargo manifest'''

        ship_inventory, keys, quantity, wap = {}, [], [], []

        for key in self.cargo:
            keys.append(key)
            quantity.append(self.return_cargo_quantity(key))
            wap.append(self.weighted_average_price(key))

        ship_inventory = {"Quantity": quantity, "Weighted Avg Price": wap}

        df = pd.DataFrame(ship_inventory, index=keys)

        prompt = f"Cargo Manifest:\n{df.to_string()}\n\nPress any key to continue."

        get_input(prompt, None, False, False, self.owner.connection)

        message_client(self.owner.connection, prompt_breaker)

    def return_cargo_quantity(self, item):
        '''Returns how much of a given item is held on the ship'''
        return sum([quantity[0] for quantity in self.cargo[item]])

    def mine_interactions(self, mines):
        '''Function handles ship interactions with non-friendly mines'''
        mine_damage = 250
        armor_mitigation = 250
        shield_mitigation = 1000
        conn = self.owner.connection

        mines_used = 1/8 * mines.quantity

        if mines_used == 0:
            mines_used = 1

        mines.deploy_or_retrieve_item(
            mines_used, False, False, False)

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
                message_client(
                    conn, "You have lost all shield and armor units.")
        else:
            # All damage mitigated

            damage_remaining = induced_damage

            if self.shields > 0:    # If the ship has shields

                shields_consumed = round(
                    damage_remaining / shield_mitigation, 2)

                if shields_consumed > self.shields:
                    damage_remaining -= (self.shields * shield_mitigation)
                    self.shields = 0
                    message_client(conn, "Shield units have been depleted.")
                else:
                    message_client(
                        conn, f"{shields_consumed} shield units have been consumed")
                    self.shields -= shields_consumed
                    damage_remaining = 0

            if damage_remaining > 0 and self.return_cargo_quantity("Armor") > 0:

                armor_consumed = damage_remaining // armor_mitigation
                message_client(conn,
                               f"{armor_consumed} armor units have been consumed from your cargo holds.")
                self.cargo["Armor"] -= armor_consumed

    def limpet_interactions(self, limpets):
        '''Attach a limpet from the deployable object to the ship and then
        Reduce quantity of deployable in sector by 1
        '''
        new_limpet = Limpet(self, limpets.owner)

        limpets.deploy_or_retrieve_item(1,
                                        False, False, False)

        self.attached_limpets.append(new_limpet)

        limpets.owner.tracked_limpets.append(new_limpet)

    def warp_disruptor_interactions(self):
        '''Warps ship to a random sector'''

        new_sector = self.current_sector
        while new_sector == self.current_sector:
            new_sector = random.randint(1, game.total_sectors)

        prompt = f"You have encountered a Warp Disruptor in sector <{self.current_sector}>. Now arriving in sector <{new_sector}>"

        message_client(self.owner.connection, prompt)

        self.change_sector(new_sector, False)

    def fighter_interactions(self, fighters):

        if fighters.mode == FighterModes.offensive:
            fighters.attack_ship(self)
            pass
        elif fighters.mode == FighterModes.defensive:
            # Don't permit ship interaction with objects in sector until fighters are destroyed
            pass
        else:
            # Charge a credit/cargo/cargo holds tax
            # If player can't pay then attack
            pass

    def ship_destroyed(self, destroyer, mines, fighters, sci_fi):
        ''''Function handles ship destruction events regardless of owner presence.'''

        self.ship_sector().ships_in_sector.remove(self)
        self.scrub_limpets()
        escape_pod_destroyed = False
        conn = self.owner.connection

        if conn != None:
            send_prompt = True
            client_msg = []
        else:
            send_prompt = False

        client_msg = []

        if self.owner_in_ship:

            if send_prompt:
                client_msg.append("Your ship has been destroyed !")

            if self.model == "Escape Pod":
                self.owner.ship = None
                escape_pod_destroyed = True
                '''!    !   !   !   !'''
                # Deny turns for the rest of the day
            else:
                # Place user in an Escape Pod in a random sector
                if send_prompt:
                    client_msg.append("Launching Escape Pods")
                escape_pod_warp = random.randint(1, game.total_sectors)

                self.owner.ship = create_new_ship(
                    0, self.owner, escape_pod_warp)

            if send_prompt:
                message_client(conn, "\n".join(client_msg))

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
        self.owner = None

    def ship_sector(self):
        '''Returns the object representing the sector the ship is currently in.'''
        return game.chart[self.current_sector]

    def scrub_limpets(self, captured_ship_new_owner=None):
        '''Remove Limpet Mines from hull. Optional arguement permits scraping only from a certain user
        Optional arguement used when capturing a ship.'''

        for limpet in self.attached_limpets:
            if captured_ship_new_owner == None or limpet.owner == captured_ship_new_owner:
                limpet.owner.tracked_limpets.remove(limpet)
                self.attached_limpets.remove(limpet)

    def change_sector(self, new_sector, lessen_fighter_response):
        '''Removes ship from the current sector and moves it to [new_sector]'''

        # Ship can no longer be interacted with by other vessels in the sector
        self.ship_sector().ships_in_sector.remove(self)

        if self.cloak_enabled:
            self.disable_cloak()

        self.current_sector = new_sector
        time.sleep(.4)
        sector_obj = self.ship_sector()
        # Show ship as an interactable in the sector
        sector_obj.ships_in_sector.append(self)
        sector_obj.load_sector(
            self.owner, lessen_fighter_response, process_events=True)

    def weighted_average_price(self, item):
        '''Returns the weighted average price of a specified commmodity'''
        cost_x_quantity = sum([commodity[0] * commodity[1]
                              for commodity in self.cargo[item]])
        try:
            return round(cost_x_quantity/self.return_cargo_quantity(item), 2)
        except ZeroDivisionError:
            return None

    def remove_cargo(self, item, quantity_to_remove):
        '''Removes cargo purchases starting with the lowest cost set'''
        current_cargo = sorted(self.cargo[item], key=lambda x: x[1])

        for pair in current_cargo:

            pair[0] -= quantity_to_remove

            if pair[0] < 0:
                quantity_to_remove = abs(pair[0])
            else:
                quantity_to_remove = 0
                break

        self.cargo[item] = [
            item_cost_pair for item_cost_pair in current_cargo if item_cost_pair[0] > 0]

    def item_selection(self):
        '''If the player presses "u" display available deployables and prompt for use.'''

        ship_items = self.useable_items
        conn = self.owner.connection
        deployable_types = []
        undeployed_quantity = []
        deployed_quantity = []
        owned_in_sector = self.ship_sector().deployables_belonging_to_player_count(self.owner)
        client_msg = []

        for item, quantity in ship_items.items():
            deployable_types.append(item)
            undeployed_quantity.append(quantity)
            try:
                deployed_quantity.append(owned_in_sector[item])
            except KeyError:
                deployed_quantity.append(0)
        else:
            utilities_df = pd.DataFrame(
                {"Deployable": deployable_types, "On Ship": undeployed_quantity, "In Sector": deployed_quantity}, index=range(1, len(deployable_types)+1))

            client_msg.append("Deployables\n")
            client_msg.append(utilities_df.to_string())
            client_msg.append("\n0 Exit\n")

        message_client(conn, "\n".join(client_msg))
        client_msg.clear()

        prompt = "Select an option from the list: \t"

        selection = get_input(prompt, range(
            len(utilities_df.index)+1), True, False, conn)

        if selection == Action.previous_menu.value:
            return
        else:
            # Get the key corresponding to the user selection
            item = utilities_df.at[selection, "Deployable"]
            available_in_sector = utilities_df.at[selection, "In Sector"]
            available_on_ship = utilities_df.at[selection, "On Ship"]
            multi_selection = False
            deploying_to_sector = False
            editing_fighter_mode = False

            if item in default_deployed.keys():

                if item == "Fighters" and available_in_sector > 0:

                    while True:

                        p1 = get_input(
                            f"Do you want to edit the mode of {item} in the sector Y/N", ["y", "n"], False, True, conn)

                        if p1 == "y":

                            editing_fighter_mode = True

                            mode_prompt = "Select new mode: (1) offensive (2) defensive (3) taxing."

                            mode = get_input(
                                mode_prompt, range(4), True, False, conn)

                            if mode == 0:
                                return

                        else:
                            editing_fighter_mode = False
                            break

                if not editing_fighter_mode:

                    if available_in_sector > 0 and available_on_ship > 0:

                        prompt = f"Do you want to <1> retrieve or <2> deploy {item} in the sector"

                        multi_selection = True

                        retrieve_or_deploy = get_input(
                            prompt, range(3), True, False, conn)

                        if retrieve_or_deploy == 0:
                            return
                        else:
                            deploying_to_sector = True if retrieve_or_deploy == 2 else False
                            editing_fighter_mode = True if retrieve_or_deploy == 3 else False

                    if ((multi_selection and deploying_to_sector) or not multi_selection) and available_on_ship > 0:

                        available_quantity = available_on_ship
                        deploying_to_sector = True

                    elif ((multi_selection and not deploying_to_sector) or not multi_selection) and available_in_sector > 0:

                        available_quantity = available_in_sector
                        deploying_to_sector = False

                    elif editing_fighter_mode:

                        available_quantity = available_in_sector and available_in_sector > 0
                        deploying_to_sector = False

                    else:

                        available_quantity = 0

            else:
                # Utility is consumed upon use
                available_quantity = available_on_ship

            if available_quantity > 0 or editing_fighter_mode:

                if item in default_deployed.keys():

                    sector_action = "deploy" if deploying_to_sector else "retrieve"

                    if not editing_fighter_mode:
                        prompt = f"How many {item} do you want to {sector_action} (0-{available_quantity})?\t"

                        quantity = get_input(prompt, range(
                            available_quantity+1), True, False, conn)

                        if quantity == 0:
                            return

                    self.owner.use_item(
                        item, quantity, deploying_to_sector, not deploying_to_sector, changing_properties=editing_fighter_mode)

                else:

                    self.owner.use_item(item, 1, True, False)
            else:
                message_client(conn,
                               f"\n{item} aren't available with the given selection.\n")
                time.sleep(1)

    def enable_cloak(self):
        '''Cloak will remain active until user tries to exit the sector
        Will hide user from Fighters in sector.'''

        self.cloak_enabled = True
        message_client(
            self.owner.connection, "Cloak activated. Cloak will remain active until you warp out of the sector.")

    def disable_cloak(self):
        self.cloak_enabled = False

        message_client(self.owner.connection, "Your cloak has been disabled.")

    def breadth_first_search(self, start, end, current_map):
        '''
        Use Breadth First Search to find shortest path for when travel cost between nodes are the same
        Optimal to use this with previous clause if the number of sectors is large
        '''
        queue = collections.deque([start])
        visited, previous_node, nodes_reached = set(), dict(), set()

        while queue:

            node = queue.popleft()
            visited.add(node)

            for connected_node in current_map[node].connected_sectors:
                # If child node is in visited then a node closer to the start is already connected
                # Checking if in nodes_reached is an optimization step to avoid repeatedly overwriting and adding the same node to the queue
                if not connected_node in visited and not connected_node in nodes_reached:

                    previous_node[connected_node] = node

                    if connected_node == end:
                        queue.clear()
                        break
                    else:
                        nodes_reached.add(connected_node)
                        queue.append(connected_node)

        connected_node = end

        path = collections.deque([])

        try:
            while connected_node != start:
                path.appendleft(connected_node)
                connected_node = previous_node[connected_node]
        except KeyError:
            return []

        return list(path)

    def dijkstra_path(self, start, end, current_map):
        '''This function is not currently used but it can be optionally enabled from the traverse_map function in the Ship class.'''

        node_cost = dict.fromkeys(current_map, np.inf)

        node_cost[start], destination_cost, predecessor, visited = 0, np.inf, dict(
        ), set()
        heap = [(0, start)]
        heapq.heapify(heap)

        while heap:  # While there are still nodes to visit

            min_node_distance, min_node = heapq.heappop(heap)

            for connected_node, edge_weight in current_map[min_node].connected_sectors.items():

                path_cost = min_node_distance + edge_weight
                # Don't bother adding nodes to the heap if their cost is greater than the cost to a found destination node
                if path_cost < node_cost[connected_node] and path_cost < destination_cost:

                    node_cost[connected_node], predecessor[connected_node] = path_cost, min_node

                    if connected_node == end:
                        # Don't place destination node in the heap
                        destination_cost = path_cost
                    elif not connected_node in visited:
                        heapq.heappush(heap, (path_cost, connected_node))
            else:
                visited.add(min_node)

        connected_node = end
        path = collections.deque([])

        while connected_node != start:
            try:
                path.appendleft(connected_node)
                connected_node = predecessor[connected_node]
            except KeyError:
                break

        if node_cost[end] != np.inf:   # If the endpoint is reachable
            return list(path)
        else:
            return []


class Deployable:
    '''This class is for items that can be placed by a player/NPC and will persist until interacted with.'''
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

        owner.ship_sector().place_deployable_in_sector(self)

    def deploy_or_retrieve_item(self, quantity, deploying_to_sector, friendly_inteaction, retrieving_from_sector=False):
        '''Edits quantity of the specified deployable...deletes from sector and player logs if quantity reaches 0.'''

        if friendly_inteaction:

            if deploying_to_sector:
                # Deployables are being added to the sector
                self.owner.ship.useable_items[self.type_] -= quantity
                self.quantity += quantity
            elif retrieving_from_sector:
                # If the owner of the item is retrieveing the deployable from a sector.
                self.owner.ship.useable_items[self.type_] += quantity
                self.quantity -= quantity
        else:
            self.quantity -= quantity

        if self.quantity <= 0:
            # If the deployed quantity has been exhausted.
            self.deployable_exhausted()

    def deployed_sector(self):
        '''Returns the object representing the sector the deployable is in.'''
        return game.chart[self.sector_num]

    def deployable_exhausted(self):
        '''Function removes the deployable from the sector and from the owner's tracked deployables.'''
        self.deployed_sector().deployed_items.remove(self)
        del self.owner.deployed[self.type_][self.sector_num]

    def attack_ship(self, ship):
        '''Function used when fighters deployed to a sector are attacking a ship.'''

        fighters_on_ship = ship.useable_items["Fighters"]
        fighters_in_sector = self.quantity

        ship.useable_items["Fighters"] -= fighters_in_sector
        self.quantity -= fighters_on_ship

        if self.quantity <= 0:
            self.deployable_exhausted()

        if ship.useable_items["Fighters"] < 0:
            ship.ship_destroyed(self.owner, False, True, False)


class Limpet:
    '''Attaches to ship hulls and reports positioning to owner when requested.'''

    def __init__(self, attached_ship, owner):
        self.attached_ship = attached_ship
        self.owner = owner

    def current_location(self):

        return self.attached_ship.current_sector


class Pilot:

    def __init__(self, name, player_credits,
                 turns_remaining, score, deployed, corporation, tracked_limpets, new_life, ship=None):

        self.name = name
        self.corporation = corporation
        self.credits = player_credits
        self.turns_remaining = turns_remaining
        self.score = score
        self.tracked_limpets = tracked_limpets
        self.connection = None

        # Dictionary for where deployables placed by player are in the world
        self.deployed = deployed

        if ship == None:

            if new_life:
                # User already has a planet.. start them in Fed Space since they died
                starting_sector = random.randint(1, 20)
            else:
                # New user detected
                starting_sector = random.randint(40, len(game.chart))

                self.ship = create_new_ship(new_ship_class=1, owner=self,
                                            spawn_sector=starting_sector)

                self.create_home_world()
        else:
            self.ship = ship

    def check_input(self, action):
        '''Function is called whenever a player creates a keyboard input while sitting in a sector outside of a planet or port'''

        message_client(self.connection, prompt_breaker)

        if action == "":  # User pressed enter
            pass

        elif action[0] == 'm':
            # Pilot wants to move sectors
            if len(action) > 1:
                # Possibly more input after the letter m
                dest = action[1:].strip()
                if dest.isdigit():
                    dest = int(dest)
                else:
                    dest = None
            else:

                nearby_sectors = " | ".join(
                    [str(element) for element in list(self.ship_sector().connected_sectors.keys())])

                message_client(self.connection,
                               '[Nearby Warps] : ' + nearby_sectors + '\n')

                dest = None

            self.ship.traverse_map(dest)
        elif action[0] == "c":
            # User wants to view ship cargo
            self.ship.show_cargo()
            self.ship_sector().load_sector(self, False, False)
        elif action[0] == "u":
            # User wants to view items available for use
            self.ship.item_selection()
            self.ship_sector().load_sector(self, True, False)
        elif action[0] == "a":
            # Choose object to attack
            pass
        elif action[0] == "l":
            # land on planet
            pass
        elif action[0] == "?":
            return_instructions(self.connection)
        elif action.isdigit():  # Used for entering Ports or Planets

            if not self.ship_sector().foreign_fighters_in_sector(self):
                action = int(action)

                try:
                    sector_obj = self.ship_sector()
                    sector_obj.ports[action].enter_port(self)
                    sector_obj.load_sector(
                        self, lessen_fighter_response=True, process_events=False)
                except KeyError:
                    pass

    def use_item(self, item, quantity, deploying_to_sector, retrieving_from_sector, mode=None, changing_properties=False):
        '''Deploy to or retrieve an item from the current sector'''
        target_sector = self.ship_sector()

        conn = self.connection

        ship_sector = self.ship.current_sector
        # Check if persistent object
        if item in default_deployed.keys():
            # Check if player already has deployables of that type in the sector
            if ship_sector in self.deployed[item]:

                deployed_item = self.deployed[item][ship_sector]

                if deploying_to_sector or retrieving_from_sector:

                    deployed_item.deploy_or_retrieve_item(
                        quantity, deploying_to_sector, True, retrieving_from_sector)

                elif changing_properties:
                    # Used for editing deployed fighter status
                    deployed_item.mode = mode

            elif deploying_to_sector:
                # Create deployable,add it to the current sector and track it
                self.add_tracked_deployable(Deployable(
                    self, item, ship_sector, quantity, mode))

        elif item == "Planet Crackers":

            available_planets = target_sector.planets_in_sector()

            if len(available_planets) > 0:
                # Print out the names of each planet and prompt user for selection
                # Destroy planet if no defenses
                pass
        elif item == "Photon Ammo":
            # Launches turn denial weapon
            # Disables Quasar cannons temporarily for 20 seconds
            pass
        elif item == "Planet Generators":
            target_sector.create_planet(planet_owner=self)
        elif item == "Cloaking Device":
            self.ship.enable_cloak()
        elif item == "Density Scanners":
            pass

        # Then remove the utility from ship
        if deploying_to_sector:
            self.ship.useable_items[item] -= quantity

    def add_tracked_deployable(self, deployable):
        '''Adds a given deployable to a pilot's deployed list for tracking'''
        # Create dictionary value using the item type and current sector as a key. Function is called when a new instance of Deployable is made
        self.deployed[deployable.type_][deployable.sector_num] = deployable

    def add_to_avoid_list(self, new_sector):
        pass
        # self.avoided_sectors.append(new_sector)

    def ship_sector(self):
        '''Returns sector object containing pilot's ship'''
        return game.chart[self.ship.current_sector]

    def claim_ship(self, ship):
        ship.owner = self

    def display_deployed(self):
        pass

    def deployable_allegiance(self, deployable):
        '''Returns whether or not a given deployable is hostile to the player.'''

        friendly = True if self is deployable.owner\
            or (deployable.owner.corporation == self.corporation
                and deployable.owner.corporation != None
                and self.corporation != None)\
            else False

        return friendly

    def create_home_world(self):

        planet_inventory = {'Ore': 0, "Organics": 0,
                            "Equipment": 0, 'Armor': 0, "Batteries": 0}

        planet_population = dict.fromkeys(planet_inventory, 1000)

        planet_class = random.randint(1, 9)

        new_planet = Planet(self, self.ship_sector(), planet_class, self.name +
                            "'s Home World", 2000, planet_population, 100, planet_inventory, None)

        self.ship_sector().planets.append(new_planet)

    def send_to_client(self, text):
        pass


class NPC:
    pass


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

    def __init__(self, sector_number, planets=None, ports_in_sector=None, connected_sectors=None, deployed_items=None, debris_percent=0, ships_in_sector=None, game_sectors_total=1_000):

        if planets == None:
            planets = []

        if deployed_items == None:
            deployed_items = []

        if ships_in_sector == None:
            ships_in_sector = []

        self.sector = sector_number
        self.deployed_items = deployed_items
        self.debirs_percent = debris_percent
        self.ships_in_sector = ships_in_sector
        self.planets = planets

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

        self.deployed_items.append(deployable)

    def load_sector(self, player, lessen_fighter_response, process_events):
        '''Displays interactabele objects and processes hazards.'''

        prompt = []
        nearby_sectors = self.connected_sectors_list()

        prompt.append(
            f'\n[Current Sector]: {self.sector}\t\t\t[Fuel remaining]: {player.turns_remaining:,}\n ')

        if len(self.planets) > 0:
            prompt.append(self.sector_planets_view())

        if self.sector == 1:
            pass
            # Load TERRA
        elif len(self.ports) > 0:

            # Print the ports in the sector
            for num, port in enumerate(self.ports.values()):
                prompt.append(f'({num+1}) {port.name}\t{port.trade_status}')

        prompt.append(f'\n[Nearby Warps] : ' + nearby_sectors + '\n')

        ships = [
            ship.ship_name for ship in self.ships_in_sector if not ship.cloak_enabled]

        if len(ships) > 0:
            prompt.append(str(ships)+"\n")

        prompt.append(prompt_breaker)

        message_client(player.connection, "\n".join(prompt))

        if process_events:
            # Deal with deployables and enviromental hazards
            self.sector_events(player, lessen_fighter_response)

    def load_terra(self):
        pass

    def generate_connecting_sectors(self, total_sectors):
        '''Function used during map generation to create a path to other sectors'''
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
        '''Creates Port objects for players to interact with'''
        sector_ports = {}

        ports_in_system = random.randint(1, 2)

        if ports_in_system > 0:

            for port_number in range(1, ports_in_system+1):

                sector_ports[port_number] = TradePort(
                    self.sector, port_number)
        return sector_ports

    def create_planet(self, planet_owner, planet=None, planet_name=None):

        if planet == None:

            planet_inventory = {'Ore': 0, "Organics": 0,
                                "Equipment": 0, 'Armor': 0, "Batteries": 0}
            planet_population = planet_inventory.copy()
            fighters = 0
            planetary_shields = 0
            planet_type = random.randint(1, 9)
            citadel = None

            if planet_name == None:
                planet_name = get_input(
                    "Enter planet name:\t", None, False, True, planet_owner.connection)

            new_planet = Planet(planet_owner, self.sector, planet_type, planet_name,
                                fighters, planet_population, planetary_shields, planet_inventory, citadel)

            self.planets.append(new_planet)

            self.load_sector(planet_owner, False, False)

        else:
            self.planets.append(planet)

    def planets_in_sector(self):

        planet_list = []
        for obj in self.deployed_items:
            if isinstance(obj, Planet):
                planet_list.append(obj)

        return planet_list

    def sector_events(self, victim, mitigate_fighters):
        '''Function handles hazardous events within sector b'''

        for deployable in self.deployed_items:

            if not victim.deployable_allegiance(deployable):

                if deployable.type == "Limpets":
                    victim.ship.limpet_interaction(deployable)

                elif deployable.type == "Mines":
                    victim.ship.mine_interactions(deployable)

                elif deployable.type == "Warp Disruptors":

                    # Increase turn count cost
                    # Or forces victim into a different sector .....possibly random sector
                    # Need photons to disable so that they can be destroyed
                    victim.ship.warp_disruptor_interactions()

                elif deployable.type == "Fighters":
                    if mitigate_fighters:
                        pass
                    else:
                        pass
        # Handle debris
        if self.debirs_percent > 0:
            pass

    def deployables_belonging_to_player_count(self, player):
        '''Returns a dictionary containing how much of each type of deployable object
         a player has placed in a sector'''

        deployed_in_sector = dict.fromkeys(default_deployed, 0)

        for deployable in self.deployed_items:
            if deployable.owner == player:
                deployed_in_sector[deployable.type_] += deployable.quantity

        return deployed_in_sector

    def density_report(self):
        '''Returns a pandas DataFrame that contains density values for a sector.'''
        pass

    def foreign_fighters_in_sector(self, player):
        for deployable in self.deployed_items:
            if deployable.type_ == "Fighters" and player.deployable_allegiance(deployable) == False:
                return True

    def connected_sectors_list(self):
        return " - ".join(
            [str(element) for element in list(self.connected_sectors.keys())])

    def sector_planets_view(self):
        planet_string = []
        planet_string.append(f'{"*"*50}')
        planet_string.append("              Planets (L)               \n")

        for planet in self.planets:
            planet_string.append(f"{planet.name}")
        else:
            planet_string.append(f'\n{"*"*50}\n')

        return "\n".join(planet_string)


class TradePort:

    def __init__(self, sector, port_number, initial_inventory=None):
        self.sector = sector
        self.name = 'Trading Port {} ~ {}'.format(sector, port_number)
        self.original = initial_inventory
        self.credits = random.randint(20_510_000, 90_700_000)
        self.inventory = self.generate_info(False)
        self.trade_status = self.port_trades_available()

    def generate_info(self, update_only_prices=False):
        '''Used to generate original inventory and prices as well as update prices to reflect
         current inventory when the optional arguement is set to True.
         '''

        if self.original == None:
            # Prices are being generated for the first time
            info = {key: {} for key in default_cargo}

            self.original = {}

            # (Quantity Range),(Price Modifier,Bsse cost)
            self.original["Ore"] = (
                30_000, 150_000), (1000, random.randint(200, 300))
            self.original["Organics"] = (
                40_000, 200_000), (2000, random.randint(100, 200))
            self.original["Armor"] = (
                60_000, 100_000), (500, random.randint(978, 1500))
            self.original["Batteries"] = (
                10_000, 45_000), (15000, random.randint(9, 12))
            self.original["Equipment"] = (
                5_000, 10_000), (800, random.randint(3000, 4000))
        else:
            info = self.inventory

        for commodity, item in info.items():

            base = self.original[commodity]

            if not update_only_prices:
                item["Quantity"] = random.randint(*base[0])
                item['Status'] = random.choice(("Buying", "Selling"))

            if item['Status'] == "Selling":
                # Higher prices with smaller WTS
                item["Price"] = round(
                    base[1][1] - item['Quantity']/base[1][0], 3)
            else:
                # Lower Prices with smaller WTB
                item["Price"] = round(
                    item['Quantity']/base[1][0] + base[1][1], 3)

        return info

    def enter_port(self, player):

        while True:
            # Update Prices to reflect current WTB/S
            self.inventory = self.generate_info(True)
            transaction_requested = False

            client_msg = []
            port_data = self.create_dataframe(player.ship)

            client_msg.append(
                f"{self.name}\tPort Funds: {round(self.credits,2):,}\t\t\tYour Balance: {round(player.credits,2):,}\n")

            client_msg.append(port_data.to_string())

            client_msg.append('\n'+prompt_breaker)

            message_client(player.connection,
                           "\n".join(client_msg))

            client_msg.clear()

            # Ask user if they want to buy/sell or exit
            prompt = "Select an option: (1) Buy from Port | (2) Sell to Port | (0) Exit port:   "

            user_selection = get_input(prompt, range(
                3), True, False, player.connection)

            message_client(player.connection,
                           prompt_breaker + "\n")

            if user_selection == Action.sell.value:
                buy_bool = False
                transaction_requested = True
            elif user_selection == Action.buy.value:
                buy_bool = True
                transaction_requested = True
            elif user_selection == Action.previous_menu.value:
                break

            if transaction_requested:
                self.buy_sell_prompt(buy_bool, player, port_data)

            message_client(player.connection,
                           prompt_breaker + "\n")

    def buy_sell_prompt(self, player_buying_status, player, inventory_df):
        '''Function asks player if they want to buy/sell, displays how much is available per user selection,
        and then prompts for quantity if trades are possible.'''
        player_ship = player.ship
        conn = player.connection

        sell_or_buy = "buy" if player_buying_status == True else "sell"

        sign = "-" if player_buying_status == True else "+"

        ship_holds_are_full = True if player_ship.holds_available() == 0\
            else False

        items_on_ship = True if player_ship.holds_available() != player_ship.total_cargo_holds\
            else False

        if player_buying_status and not ship_holds_are_full:
            choice_df = inventory_df[(inventory_df["Quantity Requested"] > 0)
                                     & (inventory_df["Status"] == "Selling")].copy()

        elif not player_buying_status:
            choice_df = inventory_df[(inventory_df["Quantity Requested"] > 0)
                                     & (inventory_df["Status"] == "Buying")
                                     & (inventory_df["Ship Inventory"] > 0)].copy()

        if (player_buying_status and not ship_holds_are_full) or not player_buying_status:
            available_for_purchase = len(choice_df.index)
        else:
            available_for_purchase = 0

        if available_for_purchase == 0:  # Check if trades aren't possible
            self.tell_user_no_trades_possible(
                items_on_ship, ship_holds_are_full, player_buying_status, conn)
            return
        else:
            choice_df.drop("Status", axis=1, inplace=True)
            choice_df.reset_index(level=0, inplace=True)
            choice_df.rename(columns={"index": "Commodity"}, inplace=True)
            choice_df.index = range(1, available_for_purchase+1)

            client_msg = []

            client_msg.append(choice_df.to_string())

            client_msg.append(f"\n0 Exit Menu\n{prompt_breaker}")

            message_client(conn,
                           "\n".join(client_msg))

            client_msg.clear()

            selection = self.prompt_for_item_selection(
                available_for_purchase, sell_or_buy, conn)

            if selection == Action.previous_menu.value:  # Equal to 0
                return
            else:

                commodity = choice_df.at[selection, "Commodity"]
                commodity_price = self.inventory[commodity]['Price']

                if player_buying_status:
                    cargo_limit = player_ship.holds_available()
                    buyer_can_afford = int(player.credits//commodity_price)
                else:
                    cargo_limit = choice_df.at[selection, "Ship Inventory"]
                    buyer_can_afford = int(self.credits//commodity_price)

                purchasable_units = min(
                    cargo_limit, buyer_can_afford, self.inventory[commodity]['Quantity'])

                message_client(conn, prompt_breaker)

                while True:  # Prompt user for how much they'd like to trade
                    # Show them how many credits they will gain or lose
                    quantity = self.prompt_for_trade_quantity(
                        sell_or_buy, purchasable_units, commodity, conn)

                    if quantity == 0:
                        return

                    transaction_cost = commodity_price * quantity

                    prompt = f'\nCurrent Balance: {round(player.credits,2):,} || New Balance: {round(player.credits + (-1* transaction_cost if player_buying_status else transaction_cost),2) :,} || Change: {sign} {round(transaction_cost,2):,}\n'
                    prompt += "Press [Enter] to confirm or [0] to cancel transaction."

                    selection = get_input(prompt, None, False, False, conn)

                    if selection == "":  # Transaction details have been confirmed
                        break
                    else:
                        return  # User wasnts to cancel transaction

                self.process_transaction(
                    quantity, commodity, player, player_buying_status)

    def process_transaction(self, quantity, item, player, player_buying):
        '''Processes buy and sell requests from players.
        Note: Check if it's poosible to do a trade before calling this function,
        IE: check if player has enough credits, empty cargo holds. Limit max quantity accordingly.
        Also check if Port has both enough credits and inventory.'''

        commodity = self.inventory[item]
        transaction_cost = quantity * commodity['Price']
        trade_conditions_met = False

        if player_buying:
            if quantity <= commodity['Quantity'] and transaction_cost <= player.credits:
                trade_conditions_met = True
                transaction_cost *= -1
                player.ship.cargo[item].append(
                    [quantity, commodity['Price']])
        else:
            # Test if port can afford the transaction
            if transaction_cost <= self.credits:
                trade_conditions_met = True
                player.ship.remove_cargo(item, quantity)

        if trade_conditions_met:
            commodity["Quantity"] -= quantity
            player.score += 1000

            self.credits -= transaction_cost
            player.credits += transaction_cost

    def steal_from_port(self, quantity, item):
        pass

    def restock(self):
        self.credits += 100_000
        self.fuel_ore += 10_000
        self.organics += 10_000
        self.armor += 10_000
        self.batteries += 10_000
        self.credits += 300_000

    def create_dataframe(self, player_ship):
        '''Creates a pandas Dataframe that shows the ports inventory and trading status.'''

        status, price, ship_inventory, keys, player_averae_bought_price, quantity_requested = [
        ], [], [], [], [], []

        for key, commodity in self.inventory.items():
            status.append(commodity["Status"])
            price.append(commodity["Price"])
            quantity_requested.append(commodity["Quantity"])
            ship_inventory.append(player_ship.return_cargo_quantity(key))
            keys.append(key)
            player_averae_bought_price.append(
                player_ship.weighted_average_price(key))

        port_df = pd.DataFrame({"Status": status,
                                "Quoted Price": price,
                                "Quantity Requested": quantity_requested,
                                "Ship Inventory": ship_inventory,
                                "Weighted Price Average": player_averae_bought_price},
                               index=keys)
        port_df.sort_index(inplace=True)

        return port_df

    def port_trades_available(self):
        '''Return first character of each commodities trade status in alphabetical order.'''
        commodity_statuses = [self.inventory[commodity]["Status"][0]
                              for commodity in sorted(self.inventory)]

        return " ".join(commodity_statuses)

    def prompt_for_item_selection(self, available_trades_count, transaction_type, conn):

        prompt = f"What would you like to {transaction_type} (0 - {available_trades_count})?\t"

        item_selection_number = get_input(
            prompt, range(available_trades_count+1), True, False, conn)

        return item_selection_number

    def prompt_for_trade_quantity(self, transaction_type, units_available, commodity_name, conn):

        prompt = f'{commodity_name} units available for purchase: {units_available:,}\n\nHow many units would you like to {transaction_type}?\t'

        quantity = get_input(prompt, range(
            units_available+1), True, False, conn)

        return quantity

    def tell_user_no_trades_possible(self, cargo_on_ship, holds_are_full, player_is_buying, conn):
        '''Need to add feature to check if port requested items >0'''

        if not player_is_buying:

            if cargo_on_ship:
                prompt = "Nothing in your inventory can be currently sold at this port."
            else:
                prompt = "You don't have any cargo on your ship\n"
        elif player_is_buying:

            if holds_are_full:
                prompt = "You don't have any available cargo holds to store additional purchases with."
            else:
                prompt = "This port isn't willing to purchase anything at this time."

        message_client(conn, prompt)

        time.sleep(.5)


class Game:

    def __init__(self, chart, saved_players=None):

        if saved_players == None:
            self.saved_players = dict()
        else:
            self.saved_players = saved_players

        self.chart = chart
        self.total_sectors = len(chart)
        self.active_players = dict()

    def add_player(self, new_player):
        self.players[new_player.name] = new_player

    def player_is_active(self, player_name):

        if player_name in self.active_players:
            return True
        else:
            return False


def join_all_sectors(current_map):
    '''Depth First Search algorithm used to find all sectors reachable from sector 1
    and then link those that are unreachable back into the primary cluster.
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


def generate_map(total_sectors=100):
    '''Generates a new map with sectors ranging from 1 upto total_sectors'''
    # Keys will be sector numbers and will hold sector objects
    current_map = {}
    for current_sector in range(1, total_sectors+1):
        # Each sector originally connects to 2 to 4 other sectors
        current_map[current_sector] = Sector(
            current_sector, game_sectors_total=total_sectors)

    # Ensure that every sector is reachable
    current_map = join_all_sectors(current_map)

    return current_map


def create_new_ship(new_ship_class, owner, spawn_sector):
    '''Returns a new Ship object'''

    attached_limpets = []
    items = default_undeployed.copy()
    cargo = default_cargo.copy()

    ship_name = "Unknown Vessel"

    if new_ship_class == 0:   # Escape Pod for when ships are destroyed while the owner is still onboard
        total_holds = 10
        warp_cost = 0
        ship_health = 500
        model = "Escape Pod"
        warp_drive_available = False
        shields = 3

    elif new_ship_class == 1:  # Default starting ship... also given to players after death
        total_holds = 1_000
        warp_cost = 2
        ship_health = 50_000
        model = "Class I"
        warp_drive_available = False
        shields = 20

    return Ship(total_holds, warp_cost, cargo, attached_limpets, items, model,
                spawn_sector, ship_name, False, ship_health, True,  warp_drive_available, shields, owner)


def default_player_properties():

    deployed_items = default_deployed.copy()

    corporation = None

    tracked_limpets = []

    turns_remaining, score, credits, = 20_000, 0, 20_000

    return deployed_items, corporation,  turns_remaining, score, credits,  tracked_limpets


def create_basic_pilot(player_name):
    '''Returns a Pilot obeject with default properties.'''

    deployed_items, corporation, turns_remaining, score, credits, tracked_limpets \
        = default_player_properties()

    user = Pilot(player_name,  credits,
                 turns_remaining, score, deployed_items, corporation,  tracked_limpets, None)

    return user


def return_instructions(client):
    instructions = "Pressing 'm' will prompt you to choose a sector to travel to.\n\n \
    Pressing 'm(number)' ex: m100 will plot a path to sector 100 can begin warping you along the plotted path.\n\n\
    When you enter a sector, if available, pressing 1 or 2 will allow you to enter the selected port.\n\n\
    Press <u> to view a list of your deployables in a sector or on your ship.\n\n\
    Press <c> to view how much of each commodity you have in your cargo holds."

    message_client(client, instructions)


def get_input(prompt, allowed_range, return_number, return_lowered_string, conn):
    '''Tells client that an input is requested. Loops until exit conditions are met'''
    prompt = PROMPT_INPUT + prompt

    while True:

        message_client(conn, prompt)

        user_input = client_response(conn)

        if return_number:

            try:
                user_input = int(user_input)
            except ValueError:
                message_client(conn, "Input a number.")
                continue

        elif return_lowered_string:
            user_input = user_input.lower()

        if allowed_range == None or user_input in allowed_range:
            return user_input
        else:
            message_client(conn, "Invalid input.")


def message_client(client, msg):
    '''There is a try and except clause in the handle_client function to handle socket errors and disconnects.'''

    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    # Pad len(message) so that it is as long as the header
    send_length += b" " * (HEADER-len(send_length))

    client.send(send_length)  # Tell client how large the message will be

    client.send(message)    # Send message


def client_response(client):
    '''Function uses socket module to await response from client.'''
    msg_length = client.recv(HEADER).decode(FORMAT)

    if msg_length:

        msg_length = int(msg_length)

        msg = client.recv(msg_length).decode(FORMAT)

        if msg == DISCONNECT_MESSAGE:
            raise OSError  # Ensure that clients disconnect cleanly
        else:
            return msg
    else:
        raise OSError


def get_login_details(conn):

    username_prompt = PROMPT_INPUT + "Enter Username >  "
    password_prompt = PROMPT_INPUT + "Enter Password >  "

    prompt_for_username = True
    account_designated = False

    while prompt_for_username:

        try:
            message_client(conn, username_prompt)
            user_name = client_response(conn)
        except OSError:
            return False, None
        # Name isn't currently in use by someone playing right now
        if not game.player_is_active(user_name):

            if user_name in game.saved_players:
                # Get password
                pass
            else:
                pilot = create_basic_pilot(user_name)
                game.saved_players[pilot.name] = pilot

            account_designated = True
            prompt_for_username = False

        else:
            message_client(conn, "Username is currently being used.")

    if account_designated:
        return True, pilot


def handle_client(conn):
    '''Prompt client for user name then asssign a Pilot object then await client input.'''

    account_designated = False
    closing_connection = False

    account_designated, pilot = get_login_details(conn)

    if account_designated:
        print(f"{pilot.name} has logged in.")
        local_network.connected_clients.append(conn)

        pilot.connection = conn

        game.active_players[pilot.name] = conn

        message_client(conn, prompt_breaker+'\n')

        pilot.ship_sector().load_sector(
            pilot, lessen_fighter_response=False, process_events=True)

        while not closing_connection:
            try:
                player_input = get_input(
                    "Select Action <?> :\t", None, False, True, conn)

                if player_input == "0":
                    closing_connection = True
                else:
                    pilot.check_input(player_input)
            except OSError:
                closing_connection = True
        else:

            del game.active_players[pilot.name]
            local_network.connected_clients.remove(conn)
            pilot.connection = None

            print(f"{pilot.name} has disconnected.")

    conn.close()


if "__main__" == __name__:

    total_sectors = 1_000

    map_ = generate_map(total_sectors)

    game = Game(map_, None)

    local_network = LocalNetwork()

    server = local_network.server

    server.listen()  # server now listening for connections

    print(f"Server is listening on {local_network.server_ip}")

    while True:
        # Code waits until a new connection is received
        conn, addr = server.accept()

        thread = threading.Thread(target=handle_client, args=(conn,))
        thread.start()

        print(f"Active connections {threading.active_count()-1}")
