# state.py

from enum import Enum

class BotState(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    RESET = "reset"
