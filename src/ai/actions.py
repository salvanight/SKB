from enum import IntEnum
from typing import Dict, Any
from gymnasium import spaces

# Attempt to import keyboard utility. If this script is run standalone for testing
# without the full project structure in PYTHONPATH, this might fail.
try:
    from src.utils import keyboard
except ImportError:
    # Fallback for testing or if src is not directly in path.
    # This allows the file to be parsed, but execute_action would fail if keyboard is not found.
    print("Warning: src.utils.keyboard could not be imported. execute_action will fail if called.")
    keyboard = None

class Action(IntEnum):
    DO_NOTHING = 0
    PRESS_ARROW_UP = 1
    PRESS_ARROW_DOWN = 2
    PRESS_ARROW_LEFT = 3
    PRESS_ARROW_RIGHT = 4
    PRESS_ATTACK_HOTKEY = 5  # Assumes a pre-configured hotkey in Tibia (e.g., Space for attack next)
    USE_HEALTH_POTION = 6
    USE_MANA_POTION = 7

def execute_action(action_id: int, context: Dict[str, Any]):
    """
    Executes a given action ID by calling the appropriate keyboard functions.
    Retrieves hotkeys from the context where necessary.
    """
    if keyboard is None:
        print("Error: keyboard module not available. Cannot execute action.")
        return

    action = Action(action_id) # Convert ID to enum member for clarity

    if action == Action.DO_NOTHING:
        pass  # No operation
    elif action == Action.PRESS_ARROW_UP:
        keyboard.press('up')
    elif action == Action.PRESS_ARROW_DOWN:
        keyboard.press('down')
    elif action == Action.PRESS_ARROW_LEFT:
        keyboard.press('left')
    elif action == Action.PRESS_ARROW_RIGHT:
        keyboard.press('right')
    elif action == Action.PRESS_ATTACK_HOTKEY:
        # For now, hardcoding 'space'. This could be made configurable later,
        # e.g., by reading from context or an AI-specific config.
        keyboard.press('space')
    elif action == Action.USE_HEALTH_POTION:
        hotkey = context.get('healing', {}).get('potions', {}).get('firstHealthPotion', {}).get('hotkey')
        if hotkey:
            keyboard.press(hotkey)
        else:
            print("Warning: Health potion hotkey not defined in context. Doing nothing.")
    elif action == Action.USE_MANA_POTION:
        hotkey = context.get('healing', {}).get('potions', {}).get('firstManaPotion', {}).get('hotkey')
        if hotkey:
            keyboard.press(hotkey)
        else:
            print("Warning: Mana potion hotkey not defined in context. Doing nothing.")
    else:
        print(f"Warning: Unknown action_id {action_id}")

# --- Gymnasium Space Definition (for reference when creating the environment) ---

# import gymnasium as gym
# from gymnasium import spaces

def get_action_space() -> spaces.Discrete:
    """
    Returns the discrete action space for the AI environment.
    """
    return spaces.Discrete(len(Action)) # Number of actions in the Action enum

# Example usage:
if __name__ == '__main__':
    if keyboard: # Only run example if keyboard module was found
        print(f"Number of defined actions: {len(Action)}")
        action_space = get_action_space()
        print(f"Action Space: {action_space}")

        # Dummy context for testing potion hotkeys
#         sample_context = {
#             'healing': {
#                 'potions': {
#                     'firstHealthPotion': {'hotkey': 'f1'},
#                     'firstManaPotion': {'hotkey': 'f2'}
#                 }
#             }
#         }
#         print("\nTesting action execution (will print warnings if hotkeys missing or keyboard is dummy):")
#         print("Executing DO_NOTHING...")
#         execute_action(Action.DO_NOTHING, sample_context)
#         print("Executing PRESS_ARROW_UP (simulated)...")
#         execute_action(Action.PRESS_ARROW_UP, sample_context)
#         print("Executing PRESS_ATTACK_HOTKEY (simulated spacebar)...")
#         execute_action(Action.PRESS_ATTACK_HOTKEY, sample_context)
#         print(f"Executing USE_HEALTH_POTION (should press F1 if keyboard util works)...")
#         execute_action(Action.USE_HEALTH_POTION, sample_context)
#         print(f"Executing USE_MANA_POTION (should press F2 if keyboard util works)...")
#         execute_action(Action.USE_MANA_POTION, sample_context)

#         # Test with missing hotkeys
#         empty_context = {}
#         print("\nTesting with empty context (should warn for potions):")
#         execute_action(Action.USE_HEALTH_POTION, empty_context)
