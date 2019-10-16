"""Class for representing a Player entity within the game."""

from game.entity import DynamicEntity


class Player(DynamicEntity):
    """A player in the game"""
    _type = 3

    def __init__(self, name: str = "Mario", max_health: float = 20):
        """Construct a new instance of the player.

        Parameters:
            name (str): The player's name
            max_health (float): The player's maximum & starting health
        """
        super().__init__(max_health=max_health)

        self._name = name
        self._score = 0
        self._jumping = False

    def get_name(self) -> str:
        """(str): Returns the name of the player."""
        return self._name

    def get_score(self) -> int:
        """(int): Get the players current score."""
        return self._score

    def is_jumping(self) -> bool:
        """(bool): Return whether or not the player is jumping currently."""
        return self._jumping

    def set_jumping(self, jumping: bool):
        """Set whether the player is currently jumping."""
        self._jumping = jumping

    def change_score(self, change: float=1):
        """Increase the players score by the given change value."""
        self._score += change

    def __repr__(self):
        return f"Player({self._name!r})"
