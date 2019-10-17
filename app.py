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
from tkinter import simpledialog, Toplevel, Message, filedialog, messagebox

import pymunk
import time
import os

from threading import Thread
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
    "flag": (5, 9),
    "tunnel": (2, 2)
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    'b': 'bounce_block',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    '^': 'cube',
    'I': 'flag',
    '=': 'tunnel',
    's': 'switch'     # Match the letter 's' on level's  file to switch class
}


LEVELS = {
    'level1.txt': 1,
    'level2.txt': 2,
    'level3.txt': 3,
    'level4.txt': 4
}

ITEMS = {
    'C': 'coin',
    '*': 'star'    # Match the symbol '*' on level's  file to Star class
}

MOBS = {
    '&': "cloud",
    '@': 'mushroom'  # Match the symbol '@' on level's  file to Mushroom class
}

BLOCK_IMAGES = {
    "brick": "brick",
    "brick_base": "brick_base",
    "cube": "cube",
    "bounce" : "bounce_block",
    "flag" : "flag",
    "tunnel" : "tunnel",
    "switch" : "switch",
    "switch_pressed" : "switch_pressed"
}

ITEM_IMAGES = {
    "coin": "coin_item",
    "star": "star"
}

MOB_IMAGES = {
    "mushroom_squished":"mushroom_squished",
    "mushroom":"mushroom",
    "cloud": "floaty",
    "fireball": "fireball_down"
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

    elif block_id == "bounce_block":  # Adding bounce, tunnel and flag to the game world
        block = BounceBlock()
    elif block_id == "flag":
        block = FlagpoleBlock()
    elif block_id == "tunnel":
        block = TunnelBlock()
    elif block_id == "switch" :
        block = switch()

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

    elif item_id == "star":  # Add Stars to the game world
        item = Star()

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

    elif mob_id == "mushroom":  # Add mushroom mob to the game world
        mob = MushroomMob()

    else:
        mob = Mob(mob_id, size=(1, 1))

    world.add_mob(mob, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_unknown(world: World, entity_id: str, x: int, y: int, *args):
    """Create an unknown entity."""
    world.add_thing(Entity(), x * BLOCK_SIZE, y * BLOCK_SIZE,
                    size=(BLOCK_SIZE, BLOCK_SIZE))



class MushroomMob(Mob):   # Mushroom extend mob class because they are similar in many points
    _id = "mushroom"

    def __init__(self):

        super().__init__(self._id, size=(16, 24), weight=0.5, tempo=80)
        self.toDestroy = False
        self.counter = 0

    def destroy(self):
        self.toDestroy = True
        self._id = "mushroom_squished"

    def step(self, time_delta, game_data):
        """Advance this mob by one time step"""
        # Track time via time_delta would be more precise, but a step counter is simpler
        # and works reasonably well, assuming time steps occur at roughly constant time deltas
        self._steps += 1
        vx = self.get_tempo()
        self.set_velocity((vx, self.get_velocity()[1]))


        if(self.toDestroy is True):
            self.counter += 1 #the counter increments on every step, so that the mushroom will be detroyed after 3 steps
            if(self.counter == 3):
                world, player = game_data
                world.remove_mob(self)



class FlagpoleBlock (Block):
    _id = "flag"

    def __init__(self):
        super().__init__()
        self._cell_size = GOAL_SIZES["flag"]

    def on_hit(self, event, data):
        world, player = data
        # Ensure the bottom of the block is being hit
        if get_collision_direction(player, self) != "A":
            return

class TunnelBlock (Block):
    _id = "tunnel"

    def __init__(self):
        super().__init__()
        self._cell_size = GOAL_SIZES["tunnel"]

    def on_hit(self, event, data):
        world, player = data
        # Ensure the bottom of the block is being hit
        if get_collision_direction(player, self) != "A":
            return


class BounceBlock(Block):
    _id = "bounce"

    def __init__(self):
        super().__init__()

    def on_hit(self, event, data):
        world, player = data
        # Ensure the bottom of the block is being hit
        if get_collision_direction(player, self) != "A":
            return

class StatusBar(tk.Frame): #the frame containing the scoreLabel and the healthLabel
    def __init__(self, master):
        super().__init__(height=4, bd=1)
        self._master = master


        #creating the scroreLabel which contains the score
        self.scoreStr = tk.StringVar()
        self._scoreLabel = tk.Button(self._master,textvariable=self.scoreStr, height=1, width=155)
        self._scoreLabel.pack()

        #creating the healthLabel which indicates the current health

        self._HealthLabel = tk.Button(self._master,text="", bg="green", height=1, width=155) #this Label's width is equal to ratio of the players health, changing color
        self._HealthLabel1 = tk.Button(self._master,text="", bg="black", height=1, width=0) # this label's width is the remaining ratio
        self._HealthLabel.pack(side=tk.LEFT)
        self._HealthLabel1.pack(side=tk.LEFT)


class Level:
    def __init__(self, name): #each level is known on the config file by the fileName, the goal, and the tunnel
        self.name = name
        self.goal = ""
        self.tunnel = ""

class TimerThread(Thread):
    # Class used to make Mario invincible for 10 seconds after collecting a star.
    # This class is a thread because The game should'nt stop when Mario collides with Star.
    # This thread runs in parallel zith the mainloop

    _timer = 0   # Counting number of seconds
    _play = Player()
    def __init__(self, player : Player):
        Thread.__init__(self)
        self._play = player

    def run(self):
        self._timer = 0
        self._play.invincible = True  # Make Mario Invincible
        while self._timer < 10 :
            time.sleep(1)    # Sleeping the thread for 1 second
            self._timer += 1
        self._play.invincible = False # Make Mario normal after 10 seconds since he has collected a star


class Star(DroppedItem):
    _id = "star"
    _play = Player()
    _timer = TimerThread(_play)
    def __init__(self):
        super().__init__()
    # Collect method for star make the player invincible for 10 seconds by launching the timer Thread
    def collect(self, player):
        self._play = player
        self._timer = TimerThread(self._play)
        self._timer.start()

class switch(Block):
    _id = "switch"
    _counter = 0
    _collisionNum = 0

    def __init__(self):
        super().__init__()
        self.pressed = False
        self.counter = 0

    def incrementcollNum(self):
        self._collisionNum += 1

    def getCollNum(self) -> int:
        return self._collisionNum
# Press the switch by changing the object from switch to switch_pressed
    dedataf on_hit(self, event, data):
        world, player, =
        if get_collision_direction(player, self) == "A":
            self._id = "switch_pressed"
            self.pressed = True
        else :
            return

    def step(self, time_delta: float, game_data):
        if self.pressed is True :
            self.counter += 1
            print(self.counter)
            if self.counter == 1000 : # the counter is 1000 when 10 seconds passed, because we have a step every 10 ms
                self._id = "switch"
                self.pressed = False
                self.counter = 0
        pass

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



class MarioApp:
    """High-level app class for Mario, a 2d platformer"""


    def setWorldProperties(self, propertie, value):

        if propertie == "gravity":
            self.gravity = int(value)
        elif propertie == "start":
            self.level = value
        else:
            self.alertFile()

    def setPlayerProperties(self, propertie, value):
        if propertie == "character":
            self.character = value
        elif propertie == "x":
            self.starting_x = int(value)
        elif propertie == "y":
            self.starting_y = int(value)
        elif propertie == "mass":
            self.mass = int(value)
        elif propertie == "health":
            self.max_health = int(value)
        elif propertie == "max_velocity":
            self.max_velocity = int(value)
        else:
            self.alertFile()

    def setLevelProperties(self, currentLevel, propertie, value):

        for level in self.levels: #iterate over the levels to get the level having the name currentName
            if level.name == currentLevel:
                theLevel = level

        if propertie == "tunnel":
            theLevel.tunnel = value
        elif propertie == "goal":
            theLevel.goal = value
        else:
            self.alertFile()

    def alertFile(self): #the alert is shown when there is wrong properties on the configuration file or on missing properties or if the file is emply
        messagebox.showerror("Warning", "Wrong configuration file")
        exit()


    def __init__(self, master):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """



        #level readed
        self._master = master
        self._master.title('Mario')
        self.down_pressed = False

        self._master.update()
        file_path = filedialog.askopenfilename()   # Openning  a view to let the user choose the configuration file
        filename, file_extension = os.path.splitext(file_path)  # Getting the extension of the selected file
        if file_extension != ".txt" :     # Show an error message box when the extension is Wrong. The extension must be .txt
            messagebox.showerror("Error", "File extension should be .txt")
            exit()

        self.levels = []

        self.load_configuration(file_path) # to load configurations from the configuration file

        world_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, self.gravity), fallback=create_unknown)
        world_builder.register_builders(BLOCKS.keys(), create_block)
        world_builder.register_builders(ITEMS.keys(), create_item)
        world_builder.register_builders(MOBS.keys(), create_mob)
        self._builder = world_builder
        self._world = load_world(world_builder, self.level)

        # Create a menu bar on the top of the game and association a function to each button on the menu with command parameter
        menubar = tk.Menu(self._master)
        menubar.add_command(label = "Load Level", command = self.showDialogInput)
        menubar.add_command(label = "Reset Level", command = self.resetLevel)
        menubar.add_command(label = "High scores", command = self.displayHighScores)
        menubar.add_command(label = "Exit", command = self.exitGame)
        self._master.config(menu = menubar)

        self._player = Player(name = self.character, max_health=self.max_health)
        self._player.invincible = False
        self._world.add_player(self._player, self.starting_x, self.starting_y, mass = self.mass)

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

    def load_configuration(self, file_path):
        with open(file_path) as fp:
            line = fp.readline()
            while line and "==World==" not in line:
                line = fp.readline()

            if not line:
                self.alertFile()

            # World line readed
            line = fp.readline()
            while line and "==Player==" not in line:
                if (":" in line):
                    self.setWorldProperties(line.split(':')[0].strip(), line.split(':')[1].strip())
                line = fp.readline()
            if not line:
                self.alertFile()

            line = fp.readline()
            while line and self.level not in line:
                if (":" in line):
                    self.setPlayerProperties(line.split(':')[0].strip(), line.split(':')[1].strip())
                line = fp.readline()

            if not line:
                self.alertFile()

            current_level = self.level

            while (line):
                self.levels.append(Level(current_level))
                line = fp.readline()
                while (line and "==" not in line):
                    if (":" in line):
                        self.setLevelProperties(current_level, line.split(':')[0].strip(), line.split(':')[1].strip())
                    line = fp.readline()
                if ("==" in line):
                    current_level = line.strip()

    def left_key(self, event): # Move Mario on the left when pressing left keypad
        self._move(-50, 0)

    def right_key(self, event):  # Move Mario on the right when pressing right keypad
        self._move(50, 0)

    def up_key(self, event):  # Move Mario up when pressing up keypad
        self._jump()

    def down_key(self, event):  # Move Mario down when pressing down keypad
        self._duck()
    #FIN
    def reset_world(self, new_level="level1.txt"):
        self.level = new_level
        self._world = load_world(self._builder, new_level)
        health = self._player.get_health()
        self._player = Player(max_health=5)
        self._player.invincible = False
        self.down_pressed = False
        self._player.change_health(health - self._player.get_max_health())
        self._world.add_player(self._player, BLOCK_SIZE, BLOCK_SIZE)

        self._setup_collision_handlers()


    def bind(self):
        #LEFT
        self._master.bind('<Left>', self.left_key)
        self._master.bind('L', self.left_key)
        #RIGHT
        self._master.bind('<Right>', self.right_key)
        self._master.bind('R', self.right_key)
        #UP
        self._master.bind('<Up>', self.up_key)
        self._master.bind('W', self.up_key)
        self._master.bind('<space>', self.up_key)
        #DOWN
        self._master.bind('<Down>', self.down_key)
        self._master.bind('S', self.down_key)



    def redraw(self):
        """Redraw all the entities in the game canvas."""
        self._view.delete(tk.ALL)

        self._view.draw_entities(self._world.get_all_things())

    #Show a dialog input after load Option in the menu.
    #The input should be an integer which coressponds to an existing Level. In our case Level 1 and 2
    # If the input is correct, we load the new level file
    def showDialogInput(self) :
        answer = simpledialog.askstring("Input", "Level number : ",parent=self._master)
        nameLevelTxt = "level"
        while(answer is None or (answer != "1" and answer !="2")) :
            answer = simpledialog.askstring("Input", " enter a correct Level number (1 or 2)  : ",parent=self._master)
        nameLevelTxt = nameLevelTxt +answer + ".txt"
        self.reset_world(nameLevelTxt)

    # Reset Score and Health of Mario
    def resetLevel(self) :
        self._player.change_score(-1*self._player.get_score())  #change score method add the parameter to the current score, so to reset the score to 0 we have just to add the -1* the currentScore
        self._player.change_health(self._player.get_max_health() - self._player.get_health()) #same for health, to reset the health to the maxHealth we have just to add the max_health - health


    def displayHighScores(self):

        top = tk.Toplevel()
        top.title("High Scores")
        try:
            f = open("HS" + self.level, "r")
        except IOError:
            f= open("HS" + self.level,"w+")

        scores = []

        f = open("HS" + self.level, "r")
        line = f.readline()
        counter = 1
        message = "" # variable containing the string to show in the message
        while line and counter < 11:
            if 'SEP' in line: #we re separating the player name and his score with the SEP
                message += str(counter) + " - " + line.split("SEP")[0].strip() + " : " + line.split("SEP")[1].strip() + "\n"
                counter = counter + 1
            line = f.readline()


        msg = Message(top, text=message, width=200)
        msg.config(font=("Courier", 12))
        msg.pack()

        button = tk.Button(top, text="Ok", command=top.destroy)
        button.pack()
        pass

    # Closing the gameView after selecting this option of menubar
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


        self.statusBar.scoreStr.set("score = " + str(self._player.get_score())) #to refresh the scoreLabel on each step
        self.statusBar._scoreLabel.pack()

        ratio = 1.0 * self._player.get_health() / self._player.get_max_health()

        #Configuring the status bar depending on health and Mario's state (Normal or invincible)
        if self._player.invincible == True :
            self.statusBar._HealthLabel.configure(bg="yellow")
        else :
            if(ratio >= 0.5):
                self.statusBar._HealthLabel.configure(bg="green")
            else:
                if(ratio > 0.25):
                    self.statusBar._HealthLabel.configure(bg="orange")
                else:
                    self.statusBar._HealthLabel.configure(bg="red")

        #in case if the health changes we have to refresh the healthLabel
        healthWidth = int(155.0 * ratio) # healthWidth change depending on the health
        self.statusBar._HealthLabel.config(width=healthWidth, height=1)
        self.statusBar._HealthLabel1.config(width=155 - healthWidth, height=1)
        self.statusBar._HealthLabel.pack(side=tk.LEFT)
        self.statusBar._HealthLabel1.pack(side=tk.LEFT)

        self._master.after(10, self.step)



    def _move(self, vx, vy):
        if(vx < 0): #moving left
            if(abs(vx) > self.max_velocity): # we have to check if velocity we set in inferior than the max velocity variable defined in the configuration file
                vx = -1 * self.max_velocity

            self._player.set_velocity((vx, 0))

        else: #moving right
            if(vx > self.max_velocity):
                vx = self.max_velocity

            self._player.set_velocity((vx, 0))


    def _jump(self):
        vy = -130
        if(vy > abs(self.max_velocity)):
            vy = -1 * self.max_velocity

        self._player.set_velocity((0, vy))


    def _duck(self):
        self.down_pressed = True
        vy = 130
        if(vy > self.max_velocity):
            vy = self.max_velocity

        self._player.set_velocity((0, vy))


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
        if(mob.get_id() == "mushroom"): #to change the mob direction when he touch a block
            if get_collision_direction(block, mob) == "L" or get_collision_direction(block, mob) == "R":
                mob.set_tempo(-1 * mob.get_tempo())

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
        if(mob1.get_id() == "mushroom"):
            mob1.set_tempo(-1 * mob1.get_tempo()) #change the mob direction => reverse the tempo
        if(mob2.get_id() == "mushroom"):
            mob2.set_tempo(-1 * mob2.get_tempo())  #change the mob direction

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

    def getNextTunnelLevel(self, current): #return the nextLevel if the player touched the tunnel using the config file
        for level in self.levels:
            if(level.name == current):
                return level.tunnel

    def getNextLevel(self, current): #return the nextLevel using the config file
        for level in self.levels:
            if(level.name == current):
                return level.goal

    def addScore(self):

        name = simpledialog.askstring("Input", "Your name : ",parent=self._master) #ask the user to insert his name
        while(name is None) :
            name = simpledialog.askstring("Input", " Your name : ",parent=self._master)

        try:
            f = open("HS" + self.level, "r")
        except IOError:  #if the file don"t exist
            f= open("HS" + self.level,"w+")

        f.close()

        scores = [] #we add all the scores sorted in this list respecting the order of the new score

        f = open("HS" + self.level, "r")
        line = f.readline()
        done = False
        while line :#iterate over the lines to find the line where we should insert the score
            if 'SEP' in line:
                if not done and self._player.get_score() > int(line.split("SEP")[1].strip()):
                    scores.append((name, self._player.get_score()))
                    done = True
                scores.append((line.split("SEP")[0].strip() , int(line.split("SEP")[1].strip())))
            line = f.readline()

        if not done: #in case if the file was emply or the user's score is less than all the others
            scores.append((name, self._player.get_score()))

        f.close()

        f= open("HS" + self.level,"w")

        for sc in scores:
            name, score = sc
            f.write(name + " SEP " + str(score) + "\n")

        f.close

    def _handle_player_collide_block(self, player: Player, block: Block, data,
                                     arbiter: pymunk.Arbiter) -> bool:

        if(block.get_id() == "bounce"):  # Propel Mario when collide to BounceBlock
            self._player.set_velocity((0, -180))

        if(block.get_id()== "flag"):
            self.addScore() #to let the player enter his name to add the score on the highscore file
            self.level = self.getNextLevel(self.level) #get the nextLevel using the config File
            self.reset_world(self.level)
            if(get_collision_direction(player, block) == "A"): #increase the player health in case his on top of the flag
                player.change_health(1)

        if(block.get_id()=="tunnel" and get_collision_direction(player, block) == "A" and self.down_pressed is True): #GO THE NEXT LEVEL IF the player pressed up on top of the tunnel
            self.level = self.getNextTunnelLevel(self.level)
            self.reset_world(self.level)

        #Removing the bricks on the left and on the right of the switch
        if block.get_id() == "switch" and get_collision_direction(player, block) == "A":
            x,y = block.get_position()
            block1 = self._world.get_block(x-GRID_WIDTH,y-block.getCollNum()*GRID_HEIGHT)
            block2 = self._world.get_block(x+GRID_WIDTH,y+block.getCollNum()*GRID_HEIGHT)
            self._world.remove_block(block1)
            self._world.remove_block(block2)
            block.incrementcollNum()

        block.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:
        # A collision with a mob make Mario Lost a health.
        # When Mario is Invincible Mario Lost and gain a life.
        # Thus, the health don't change tough the collision heppened
        if player.invincible == True :
            player.change_health(1)

        if(type(mob) is MushroomMob):
            if get_collision_direction(player, mob) == "A": #in case if the player is above the mushroomMob
                player.set_velocity((0, 100)) #the player up
                mob.destroy() #destroy the mob
            else:#in case the collision is on another direction
                player.change_health(-1) #the player should lose health
                player.set_velocity((2 * mob.get_velocity()[0], 0)) , #the player should be slightly repelled away

        mob.on_hit(arbiter, (self._world, player))
        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:
        return True


root = tk.Tk()
app = MarioApp(root)
