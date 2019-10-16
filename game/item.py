"""
Classes to represent items dropped within the game world that players pickup.
"""

from game.entity import DynamicEntity


class DroppedItem(DynamicEntity):
    """An item dropped within the game world.

    Dropped items must implement the collect(Player) method to handle players
    picking up the items.
    """
    _id = None
    _type = 4

    def get_id(self) -> str:
        """(str) Returns the unique id of this block"""
        return self._id

    def collect(self, player):
        """Collect method activated when a player collides with the item.

        Parameters:
            player (Player): The player which collided with the dropped item.
        """
        raise NotImplementedError("Should be overridden in a subclass")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.get_id()})"


class Coin(DroppedItem):
    """A dropped coin item that can be picked up to increment the players score.
    """
    _id = "coin"

    def __init__(self, value: int=1):
        """Construct a coin with a score value of value.

        Parameters:
            value (int): The value of the coin
        """
        super().__init__()
        self._value = value

    def collect(self, player):
        """Collect the coin and increment the players score by the coin value."""
        player.change_score(self._value)
