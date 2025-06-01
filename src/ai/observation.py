from typing import List, Dict, Any
import numpy as np
import gymnasium as gym # Ensure gymnasium is imported
from gymnasium import spaces # Ensure spaces is imported

def extract_observation(context: Dict[str, Any]) -> np.ndarray:
    """
    Extracts a numerical observation vector from the bot's context.
    Handles potential None values by substituting defaults.
    """

    # Player Stats
    hp_percentage = context.get('ng_statusBar', {}).get('hpPercentage', 0.0)
    if hp_percentage is None:
        hp_percentage = 0.0

    mana_percentage = context.get('ng_statusBar', {}).get('manaPercentage', 0.0)
    if mana_percentage is None:
        mana_percentage = 0.0

    # Targeting/Combat
    has_target = 1 if context.get('ng_cave', {}).get('targetCreature') is not None else 0

    game_window_monsters = context.get('gameWindow', {}).get('monsters', [])
    num_monsters_on_screen = len(game_window_monsters) if game_window_monsters is not None else 0

    is_being_attacked = 1 if context.get('ng_battleList', {}).get('beingAttackedCreatureCategory') is not None else 0

    # Player Position
    radar_coord = context.get('ng_radar', {}).get('coordinate')
    if radar_coord:
        pos_x = radar_coord.get('x', -1)
        pos_y = radar_coord.get('y', -1)
        pos_z = radar_coord.get('z', -1)
    else:
        pos_x, pos_y, pos_z = -1, -1, -1

    observation = np.array([
        hp_percentage,
        mana_percentage,
        has_target,
        num_monsters_on_screen,
        is_being_attacked,
        pos_x,
        pos_y,
        pos_z
    ], dtype=np.float32)

    return observation

# --- Gymnasium Space Definition (for reference when creating the environment) ---

def get_observation_space() -> spaces.Box:
    """
    Returns the observation space for the AI environment.
    """
    # Define low and high bounds for each feature
    # hp_percentage, mana_percentage: 0.0 to 1.0
    # has_target, is_being_attacked: 0 to 1 (binary)
    # num_monsters_on_screen: 0 to e.g., 50 (assuming max 50 monsters on screen)
    # pos_x, pos_y, pos_z: -1 (unknown/default) up to map limits (e.g., 30000 if Tibia map size)
    #                        Using a large general range for now.
    low = np.array([
        0.0,  # hp_percentage
        0.0,  # mana_percentage
        0,    # has_target
        0,    # num_monsters_on_screen
        0,    # is_being_attacked
        -1,   # pos_x (or map_min_x)
        -1,   # pos_y (or map_min_y)
        -1    # pos_z (or map_min_z)
    ], dtype=np.float32)

    high = np.array([
        1.0,  # hp_percentage
        1.0,  # mana_percentage
        1,    # has_target
        50,   # num_monsters_on_screen (adjust as needed)
        1,    # is_being_attacked
        30000, # pos_x (or map_max_x)
        30000, # pos_y (or map_max_y)
        15     # pos_z (or map_max_z)
    ], dtype=np.float32)

    return spaces.Box(low=low, high=high, dtype=np.float32)

# Example usage:
if __name__ == '__main__':
    # Dummy context for testing
    sample_context = {
#         'ng_statusBar': {'hpPercentage': 0.75, 'manaPercentage': 0.50},
#         'ng_cave': {'targetCreature': {'name': 'Dragon'}},
#         'gameWindow': {'monsters': [{'name': 'Dragon'}, {'name': 'Dragon Lord'}]},
#         'ng_battleList': {'beingAttackedCreatureCategory': 'monster'},
#         'ng_radar': {'coordinate': {'x': 123, 'y': 456, 'z': 7}}
#     }
#     observation = extract_observation(sample_context)
#     print(f"Observation: {observation}")
#
#     obs_space = get_observation_space()
#     print(f"Observation Space: {obs_space}")
#     if obs_space.contains(observation):
#         print("Sample observation is valid within the defined space.")
#     else:
#         # This might happen if e.g. num_monsters > high bound or coords are outside range
#         print("Sample observation is NOT valid within the defined space.")
#         # Check individual elements
#         for i, val in enumerate(observation):
#             if not (obs_space.low[i] <= val <= obs_space.high[i]):
#                 print(f"Element {i} (value: {val}) is out of bounds [{obs_space.low[i]}, {obs_space.high[i]}]")
