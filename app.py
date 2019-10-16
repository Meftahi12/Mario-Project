"""
Simple 2d world where the player can interact with the items in the world.
"""
from multiprocessing import Process

from pynput.keyboard import Listener, Key

__author__ = ""
__date__ = ""
__version__ = "1.0.0"
__copyright__ = "The University of Queensland, 2019"

import math
import tkinter as tk
from typing import Tuple, List
from tkinter import simpledialog

import pymunk

from game.block import Block, MysteryBlock
from game.item import DroppedItem
from game.entity import Entity, BoundaryWall
from game.mob import Mob, CloudMob, Fireball
from game.view import GameView, ViewRenderer
from game.util import get_collision_direction
from game.item import Coin
from game.world import World

from player import Player
from level import load_world, WorldBuilder

BLOCK_SIZE = 2 ** 4
GRID_WIDTH = 2 ** 4
GRID_HEIGHT = 2 ** 4
SCROLL_RADIUS = 50
MAX_WINDOW_SIZE = (1080, math.inf)

GOAL_SIZES = {
    "flag": (0.2, 9),
    "tunnel": (2, 2)
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    'b': 'bounce_block',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    '^': 'cube',
}

ITEMS = {
    'C': 'coin'
}

MOBS = {
    '&': "cloud"
}


def create_block(world: World, block_id: str, x: int, y: int, *args):
    """Create a new block instance and add it to the world based on the block_id.

    Parameters:
        world (World): The world where the block should be added to.
        block_id (str): The block identifier of the block to create.
        x (int): The x coordinate of the block.
        y (int): The y coordinate of the block.
    """
    block_id = BLOCKS[block_id]
    if block_id == "mystery_empty":
        block = MysteryBlock()
    elif block_id == "mystery_coin":
        block = MysteryBlock(drop="coin", drop_range=(3, 6))
    elif block_id == "bounce_block":
        block = BounceBlock()
    else:
        block = Block(block_id)

    world.add_block(block, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_item(world: World, item_id: str, x: int, y: int, *args):
    """Create a new item instance and add it to the world based on the item_id.

    Parameters:
        world (World): The world where the item should be added to.
        item_id (str): The item identifier of the item to create.
        x (int): The x coordinate of the item.
        y (int): The y coordinate of the item.
    """
    item_id = ITEMS[item_id]
    if item_id == "coin":
        item = Coin()
    else:
        item = DroppedItem(item_id)

    world.add_item(item, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_mob(world: World, mob_id: str, x: int, y: int, *args):
    """Create a new mob instance and add it to the world based on the mob_id.

    Parameters:
        world (World): The world where the mob should be added to.
        mob_id (str): The mob identifier of the mob to create.
        x (int): The x coordinate of the mob.
        y (int): The y coordinate of the mob.
    """
    mob_id = MOBS[mob_id]
    if mob_id == "cloud":
        mob = CloudMob()
    elif mob_id == "fireball":
        mob = Fireball()
    else:
        mob = Mob(mob_id, size=(1, 1))

    world.add_mob(mob, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_unknown(world: World, entity_id: str, x: int, y: int, *args):
    """Create an unknown entity."""
    world.add_thing(Entity(), x * BLOCK_SIZE, y * BLOCK_SIZE,
                    size=(BLOCK_SIZE, BLOCK_SIZE))


BLOCK_IMAGES = {
    "brick": "brick",
    "brick_base": "brick_base",
    "cube": "cube",
}

ITEM_IMAGES = {
    "coin": "coin_item",
}

MOB_IMAGES = {
    "cloud": "floaty",
    "fireball": "fireball_down"
}

class BounceBlock(Block):
    _id = "bounce"

    def __init__(self):
        super().__init__()

    def on_hit(self, event, data):
        world, player = data
        # Ensure the bottom of the block is being hit
        if get_collision_direction(player, self) != "A":
            return

    def propelMario(self, player):
        player.set_velocity((0, -130))


class MarioViewRenderer(ViewRenderer):
    """A customised view renderer for a game of mario."""

    @ViewRenderer.draw.register(Player)
    def _draw_player(self, instance: Player, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if shape.body.velocity.x >= 0:
            image = self.load_image("mario_right")
        else:
            image = self.load_image("mario_left")
        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="player")]

    @ViewRenderer.draw.register(MysteryBlock)
    def _draw_mystery_block(self, instance: MysteryBlock, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image("coin")
        else:
            image = self.load_image("coin_used")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

    @ViewRenderer.draw.register(BounceBlock)
    def _draw_bounce_block(self, instance: BounceBlock, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:

        image = self.load_image("bounce_block")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

class StatusBar(tk.Frame):
    def __init__(self, master):
        super().__init__(height=4, bd=1)
        self._master = master

        self.scoreStr = tk.StringVar()
        self._scoreLabel = tk.Button(self._master,textvariable=self.scoreStr, height=1, width=155)
        self._scoreLabel.pack()

        self._HealthLabel = tk.Button(self._master,text="", bg="green", height=1, width=155)
        self._HealthLabel1 = tk.Button(self._master,text="", bg="black", height=1, width=0)
        self._HealthLabel.pack(side=tk.LEFT)
        self._HealthLabel1.pack(side=tk.LEFT)




class MarioApp:
    """High-level app class for Mario, a 2d platformer"""

    def __init__(self, master):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """
        self.dx = 0
        self.dy = 0
        self._master = master
        self._master.title('Mario')

        world_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, 300), fallback=create_unknown)
        world_builder.register_builders(BLOCKS.keys(), create_block)
        world_builder.register_builders(ITEMS.keys(), create_item)
        world_builder.register_builders(MOBS.keys(), create_mob)
        self._builder = world_builder

        self._world = load_world(world_builder, "level1.txt")

        menubar = tk.Menu(self._master)
        menubar.add_command(label = "Load Level", command = self.showDialogInput)
        menubar.add_command(label = "Reset Level", command = self.resetLevel)
        menubar.add_command(label = "Exit", command = self.exitGame)
        self._master.config(menu = menubar)

        self._player = Player(max_health=5)
        self._world.add_player(self._player, BLOCK_SIZE, BLOCK_SIZE)

        self._setup_collision_handlers()

        self._renderer = MarioViewRenderer(BLOCK_IMAGES, ITEM_IMAGES, MOB_IMAGES)

        size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._world.get_pixel_size())))
        self._view = GameView(master, size, self._renderer)
        self._view.pack()
        self.bind()

        # Wait for window to update before continuing
        master.update_idletasks()

        self.statusBar = StatusBar(self._master)

        self.step()
        self._master.mainloop()


#DEBUT

    def left_key(self, event):
        self._player.set_velocity((-50, 0))

    def right_key(self, event):
        self._player.set_velocity((50, 0))

    def up_key(self, event):
        self._player.set_velocity((0, -130))

    def down_key(self, event):
        self._player.set_velocity((0, 130))

#FIN
    def reset_world(self, new_level="level1.txt"):
        self._world = load_world(self._builder, new_level)

        self._player = Player()
        self._world.add_player(self._player, BLOCK_SIZE, BLOCK_SIZE)

        self._setup_collision_handlers()


#DEBUT
    def bind(self):
        self._master.bind('<Left>', self.left_key)
        self._master.bind('<Right>', self.right_key)
        self._master.bind('<Up>', self.up_key)
        self._master.bind('<Down>', self.down_key)
#FIN



    def redraw(self):
        """Redraw all the entities in the game canvas."""
        self._view.delete(tk.ALL)

        self._view.draw_entities(self._world.get_all_things())

    def showDialogInput(self) :
        answer = simpledialog.askstring("Input", "Level number : ",parent=self._master)
        nameLevelTxt = "level"
        while(answer is None or (answer != "1" and answer !="2")) :
            answer = simpledialog.askstring("Input", " enter a correct Level number (1 or 2)  : ",parent=self._master)
        nameLevelTxt = nameLevelTxt +answer + ".txt"
        print(nameLevelTxt)
        self.reset_world(nameLevelTxt)

    def resetLevel(self) :
        self._player.change_score(-1*self._player.get_score())
        self._player.change_score(self._player.change_health(self._player.get_max_health()-self._player.get_health()))
        print(self._player.get_score())

    def exitGame(self):
        exit()

    def scroll(self):
        """Scroll the view along if the player is within SCROLL_RADIUS
        from the edge of the screen.
        """
        # calculate the x distance from the right edge
        x_position = self._player.get_position()[0]
        x_offset = self._view.get_offset()[0]
        screen_size = self._master.winfo_width()
        edge_distance = screen_size - (x_position + x_offset)

        if edge_distance < SCROLL_RADIUS:
            x_position -= 5

            # place a backstop boundary wall on the left side of the screen
            # to prevent the player from going backwards in the game
            world_space = self._world.get_space()
            wall = BoundaryWall("backstop", world_space.static_body,
                                (x_position, 0),
                                (x_position, self._world.get_pixel_size()[1]), 5)
            world_space.add(wall.get_shape())

            # shift the view offset by the screen size
            self._view.shift((-(screen_size - SCROLL_RADIUS), 0))

    def step(self):
        """Step the world physics and redraw the canvas."""
        data = (self._world, self._player)


        self._world.step(data)

        self.scroll()
        self.redraw()


        self.statusBar.scoreStr.set("score = " + str(self._player.get_score()))
        self.statusBar._scoreLabel.pack()

        ratio = 1.0 * self._player.get_health() / self._player.get_max_health()

        if(ratio >= 0.5):
            self.statusBar._HealthLabel.configure(bg="green")
        else:
            if(ratio > 0.25):
                self.statusBar._HealthLabel.configure(bg="orange")
            else:
                self.statusBar._HealthLabel.configure(bg="red")

        healthWidth = int(155.0 * ratio)
        self.statusBar._HealthLabel.config(width=healthWidth, height=1)
        self.statusBar._HealthLabel1.config(width=155 - healthWidth, height=1)
        self.statusBar._HealthLabel.pack(side=tk.LEFT)
        self.statusBar._HealthLabel1.pack(side=tk.LEFT)

        self._master.after(10, self.step)



    def _move(self, dx, dy):
        self.dx = dx
        self.dy = dy


    def _jump(self):
        pass

    def _duck(self):
        pass

    def _setup_collision_handlers(self):
        self._world.add_collision_handler("player", "item", on_begin=self._handle_player_collide_item)
        self._world.add_collision_handler("player", "block", on_begin=self._handle_player_collide_block,
                                          on_separate=self._handle_player_separate_block)
        self._world.add_collision_handler("player", "mob", on_begin=self._handle_player_collide_mob)
        self._world.add_collision_handler("mob", "block", on_begin=self._handle_mob_collide_block)
        self._world.add_collision_handler("mob", "mob", on_begin=self._handle_mob_collide_mob)
        self._world.add_collision_handler("mob", "item", on_begin=self._handle_mob_collide_item)


    def _handle_mob_collide_block(self, mob: Mob, block: Block, data,
                                  arbiter: pymunk.Arbiter) -> bool:
        if mob.get_id() == "fireball":
            if block.get_id() == "brick":
                self._world.remove_block(block)
            self._world.remove_mob(mob)
        return True


    def _handle_mob_collide_item(self, mob: Mob, block: Block, data,
                                 arbiter: pymunk.Arbiter) -> bool:
        return False

    def _handle_mob_collide_mob(self, mob1: Mob, mob2: Mob, data,
                                arbiter: pymunk.Arbiter) -> bool:
        if mob1.get_id() == "fireball" or mob2.get_id() == "fireball":
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)

        return False

    def _handle_player_collide_item(self, player: Player, dropped_item: DroppedItem,
                                    data, arbiter: pymunk.Arbiter) -> bool:
        """Callback to handle collision between the player and a (dropped) item. If the player has sufficient space in
        their to pick up the item, the item will be removed from the game world.

        Parameters:
            player (Player): The player that was involved in the collision
            dropped_item (DroppedItem): The (dropped) item that the player collided with
            data (dict): data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter): Data about a collision
                                      (see http://www.pymunk.org/en/latest/pymunk.html#pymunk.Arbiter)
                                      NOTE: you probably won't need this
        Return:
             bool: False (always ignore this type of collision)
                   (more generally, collision callbacks return True iff the collision should be considered valid; i.e.
                   returning False makes the world ignore the collision)
        """

        dropped_item.collect(self._player)
        self._world.remove_item(dropped_item)
        return False

    def _handle_player_collide_block(self, player: Player, block: Block, data,
                                     arbiter: pymunk.Arbiter) -> bool:

        if(type(block) is BounceBlock):
            print("haa")
            self._player.set_velocity((0, -180))

        block.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:
        mob.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:
        return True


root = tk.Tk()
app = MarioApp(root)
