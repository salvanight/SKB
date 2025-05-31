import gymnasium as gym
from gymnasium import spaces
import numpy as np
import copy
from typing import Tuple, Dict, Any, Optional

try:
    from src.ai.actions import Action, execute_action # Assuming get_action_space will be here or Action used directly
    from src.ai.observation import extract_observation # Assuming get_observation_space will be here
    from src.ai.reward import calculate_reward
    # For action/observation space definitions. If they are not in actions.py/observation.py, adjust path or define here.
    # These are placeholders; actual function names might differ or be part of the class itself.
    # It's common to define these spaces directly in the Env __init__ or have helper functions in actions.py/observation.py

    # Attempt to get space definition functions. If these specific names don't exist,
    # the environment will rely on the dummy definitions provided in the except block,
    # or these need to be adjusted to the actual function names.
    try:
        from src.ai.actions import get_action_space
    except ImportError:
        print("Warning: get_action_space not found in src.ai.actions. Using dummy if Action enum is available.")
        if 'Action' in locals() and Action is not None:
            get_action_space = lambda: spaces.Discrete(len(Action))
        else:
            get_action_space = lambda: spaces.Discrete(8) # Fallback dummy

    try:
        from src.ai.observation import get_observation_space
    except ImportError:
        print("Warning: get_observation_space not found in src.ai.observation. Using dummy.")
        get_observation_space = lambda: spaces.Box(low=0, high=1, shape=(8,), dtype=np.float32) # Fallback dummy


except ImportError as e:
    print(f"Warning: Could not import AI modules in env.py: {e}. Ensure they exist and PYTHONPATH is correct.")
    # Define dummies if needed for the script to parse, though it won't function.
    # Ensure critical modules like Action are defined, even if as None, before class definition.
    if 'Action' not in locals(): Action = None
    if 'execute_action' not in locals(): execute_action = None
    if 'extract_observation' not in locals(): extract_observation = None
    if 'calculate_reward' not in locals(): calculate_reward = None
    if 'get_action_space' not in locals():
        get_action_space = lambda: spaces.Discrete(8)
        print("env.py: Using dummy get_action_space due to top-level import error.")
    if 'get_observation_space' not in locals():
        get_observation_space = lambda: spaces.Box(low=0, high=1, shape=(8,), dtype=np.float32)
        print("env.py: Using dummy get_observation_space due to top-level import error.")

class TibiaAIEnv(gym.Env):
    metadata = {'render_modes': [], 'render_fps': 4} # FPS is arbitrary here

    def __init__(self, bot_context_manager, legacy_game_loop_thread_instance):
        """
        Initializes the Tibia AI Environment.

        Args:
            bot_context_manager: The bot's context manager (wrapper around the main context dict).
            legacy_game_loop_thread_instance: Instance of LegacyGameLoopThread, needed for handleGameData.
                                            This will ideally be refactored to a single step function.
        """
        super().__init__()

        if Action is None or extract_observation is None or calculate_reward is None or execute_action is None: # Check if imports failed
            raise ImportError("Critical AI modules (Action, extract_observation, etc.) not imported. Environment cannot function.")

        self.bot_context_manager = bot_context_manager
        self.game_loop_thread = legacy_game_loop_thread_instance # Store the instance

        # Define action and observation spaces
        self.action_space = get_action_space()
        self.observation_space = get_observation_space()

        self.previous_context: Optional[Dict[str, Any]] = None
        self.previous_observation: Optional[np.ndarray] = None

        # This will be the refactored method from LegacyGameLoopThread
        # For now, we'll directly call handleGameData and related logic inside step()
        # self.game_loop_step_function = legacy_game_loop_thread_instance._run_one_ai_step


    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed) # Important for reproducibility if seed is used

        print("TibiaAIEnv: Resetting environment...")
        # Ensure bot is not paused (actual pause state is in the context dict)
        # TODO: Standardize pause key, e.g., context['bot_paused']
        if 'ng_pause' in self.bot_context_manager.context:
             self.bot_context_manager.context['ng_pause'] = False
        if 'py_pause' in self.bot_context_manager.context:
             self.bot_context_manager.context['py_pause'] = False


        # Perform an initial perception step to get the first observation
        # Note: This assumes _run_perception_step can be called safely.
        self.game_loop_thread._run_perception_step() # This updates self.game_loop_thread.context.context
                                                     # which is the same object as self.bot_context_manager.context

        self.previous_context = copy.deepcopy(self.bot_context_manager.context)
        self.previous_observation = extract_observation(self.previous_context)

        if not self.observation_space.contains(self.previous_observation):
            print(f"Warning: Initial observation {self.previous_observation} is not contained in observation space {self.observation_space}.")
            # Potentially clip or re-normalize if this happens, or adjust space definition.

        print(f"TibiaAIEnv: Reset complete. Initial observation shape: {self.previous_observation.shape}")
        return self.previous_observation, {}

    def step(self, action_id: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        if self.previous_context is None or self.previous_observation is None:
            raise RuntimeError("Environment reset() must be called before step().")

        if not isinstance(action_id, int):
            # If action_id is numpy.int64 or similar, cast to Python int
            action_id = int(action_id)


        # 1. Execute AI action (modifies context internally via keyboard commands, then game state)
        execute_action(action_id, self.bot_context_manager.context)

        # 2. Run bot's perception logic to update context based on new game state
        # This is the part that needs careful handling with the existing game loop.
        # A short sleep might be needed if actions take time to reflect in game & screenshot.
        # import time
        # time.sleep(0.05) # Small delay for game state to update after action, adjust as needed
        self.game_loop_thread._run_perception_step() # This updates self.game_loop_thread.context.context
                                                     # which is the same object as self.bot_context_manager.context

        current_context = copy.deepcopy(self.bot_context_manager.context)
        current_observation = extract_observation(current_context)

        if not self.observation_space.contains(current_observation):
            print(f"Warning: Current observation {current_observation} is not contained in observation space {self.observation_space}.")
            # Potentially clip or re-normalize. For now, just warn.


        # 3. Determine if the episode is done (e.g., player died)
        hp_percentage = current_context.get('ng_statusBar', {}).get('hpPercentage', 0.0)
        if hp_percentage is None: hp_percentage = 0.0 # Treat None HP as 0 for safety
        done = hp_percentage == 0.0

        # 4. Calculate reward
        reward = calculate_reward(self.previous_context, current_context, action_id)

        # Update previous state trackers
        self.previous_context = current_context
        self.previous_observation = current_observation

        # 5. Return: observation, reward, terminated, truncated, info
        # terminated = done (game over condition)
        # truncated = False (not implementing time limits for now)
        return current_observation, reward, done, False, {}

    def render(self):
        # For now, we don't have a separate rendering. The game itself is the rendering.
        pass

    def close(self):
        # Any cleanup logic (e.g., stopping threads, if the env managed them)
        print("TibiaAIEnv: Closing environment.")
        pass

# Note: The actual get_action_space_from_enum and get_observation_space_definition
# functions should be implemented in src/ai/actions.py and src/ai/observation.py respectively.
# Example stubs for what they might look like:

# In src/ai/actions.py:
# from enum import IntEnum
# from gymnasium import spaces
# class Action(IntEnum): ...
# def get_action_space_from_enum(): return spaces.Discrete(len(Action))

# In src/ai/observation.py:
# import numpy as np
# from gymnasium import spaces
# def get_observation_space_definition():
#   low = np.array([...]) # Define actual low bounds for each feature
#   high = np.array([...]) # Define actual high bounds for each feature
#   return spaces.Box(low=low, high=high, dtype=np.float32)


if __name__ == '__main__':
    # This is a conceptual test. It requires a mocked/dummy bot_context_manager
    # and legacy_game_loop_thread_instance to run.
    print("Conceptual test for TibiaAIEnv:")

    # --- Mocking dependencies ---
    class MockContextManager:
        def __init__(self):
            self.context = {
                'ng_pause': True, 'py_pause': True,
                'ng_statusBar': {'hpPercentage': 1.0, 'manaPercentage': 1.0},
                'ng_cave': {'targetCreature': None, 'isAttackingSomeCreature': False},
                'gameWindow': {'monsters': []},
                'ng_battleList': {'beingAttackedCreatureCategory': None},
                'ng_radar': {'coordinate': {'x': 0, 'y': 0, 'z': 0}},
                'healing': { # For potion hotkeys in execute_action
                    'potions': {
                        'firstHealthPotion': {'hotkey': 'f1'},
                        'firstManaPotion': {'hotkey': 'f2'}
                    }
                }
            }

    class MockLegacyGameLoopThread:
        def __init__(self, context_manager_ref):
            self.context_manager = context_manager_ref

        def handleGameData(self, context_dict):
            # Simulate game data update:
            if context_dict['ng_statusBar']['hpPercentage'] > 0:
                # Simulate potential HP loss unless a "potion" was "used" by an action
                if not hasattr(self, '_acted_heal'): # Crude check if a healing action was simulated
                    context_dict['ng_statusBar']['hpPercentage'] = max(0.0, context_dict['ng_statusBar']['hpPercentage'] - np.random.uniform(0.0, 0.05))
                self._acted_heal = False # Reset flag

            if np.random.rand() < 0.1 and not context_dict['gameWindow']['monsters'] and context_dict['ng_statusBar']['hpPercentage'] > 0:
                 context_dict['gameWindow']['monsters'].append({'name': 'mock_monster'})
                 context_dict['ng_cave']['targetCreature'] = {'name': 'mock_monster'}
                 context_dict['ng_cave']['isAttackingSomeCreature'] = True
                 print("  (Mock monster appeared)")

            context_dict['ng_radar']['coordinate']['x'] += np.random.randint(-1, 2)
            context_dict['ng_radar']['coordinate']['y'] += np.random.randint(-1, 2)
            return context_dict

        # Mock execute_action's effect slightly for testing rewards
        def mock_action_effect(self, action_id, context_dict):
            try:
                action_enum = Action(action_id)
                if action_enum == Action.USE_HEALTH_POTION and context_dict['ng_statusBar']['hpPercentage'] < 1.0:
                    context_dict['ng_statusBar']['hpPercentage'] = min(1.0, context_dict['ng_statusBar']['hpPercentage'] + 0.3) # Simulate heal
                    self._acted_heal = True # Signal that heal occurred
                    print("  (Simulated health potion effect)")
                elif action_enum == Action.PRESS_ATTACK_HOTKEY:
                     if context_dict['ng_cave']['targetCreature'] and context_dict['ng_statusBar']['hpPercentage'] > 0:
                         context_dict['gameWindow']['monsters'] = []
                         context_dict['ng_cave']['targetCreature'] = None
                         context_dict['ng_cave']['isAttackingSomeCreature'] = False
                         print("  (Simulated a kill due to attack action)")
            except (ValueError, NameError): # Action enum might not be fully available if imports failed
                pass


    # --- End Mocking ---

    if Action is not None and extract_observation is not None and calculate_reward is not None and execute_action is not None:
        print("Attempting to initialize mock environment...")
        mock_ctx_mgr = MockContextManager()
        mock_loop_thread = MockLegacyGameLoopThread(mock_ctx_mgr)

        # Replace real execute_action with a mock for this test, to simulate its effects on context
        original_execute_action = execute_action
        def mocked_execute_action_for_env_test(action_id, context):
            # Call the mock effect simulation
            mock_loop_thread.mock_action_effect(action_id, context)
            # original_execute_action(action_id, context) # We could call original if it didn't rely on real keyboard
            # For this test, we just want to see if the context changes in a way reward func can see
            # print(f"Mocked execute_action called with action_id: {action_id}")
            pass # No actual keyboard press

        # Temporarily replace execute_action in the global scope of this test
        # This is a bit hacky; ideally, the env would allow injecting a mock action executor.
        # globals()['execute_action'] = mocked_execute_action_for_env_test
        # Better: Pass it to the env or have the env use a method that can be overridden.
        # For now, the mock_action_effect is called separately in the loop below.

        env = TibiaAIEnv(bot_context_manager=mock_ctx_mgr, legacy_game_loop_thread_instance=mock_loop_thread)

        print(f"Action Space: {env.action_space}")
        print(f"Observation Space: {env.observation_space}")

        obs, info = env.reset()
        print(f"Initial observation from reset: {obs[0]:.2f} HP%, {obs[1]:.2f} MP%, Target: {obs[2]}, Monsters: {obs[3]}, Attacked: {obs[4]}, Pos: ({obs[5]},{obs[6]},{obs[7]})")

        for i in range(10): # More steps for better chance of seeing different scenarios
            action = env.action_space.sample()
            action_name = Action(action).name if Action else "N/A"
            print(f"\nStep {i+1}, Chosen Action: {action} ({action_name})")

            # Simulate the effect of the chosen action on the mock context BEFORE env.step()
            # This is because the real execute_action would modify game state before handleGameData sees it.
            mock_loop_thread.mock_action_effect(action, mock_ctx_mgr.context)

            obs, reward, terminated, truncated, info = env.step(action)
            print(f"  -> Obs: {obs[0]:.2f} HP%, {obs[1]:.2f} MP%, Target: {obs[2]}, Monsters: {obs[3]}, Attacked: {obs[4]}, Pos: ({obs[5]},{obs[6]},{obs[7]})")
            print(f"  -> Reward: {reward:.2f}, Terminated: {terminated}")

            if terminated:
                print("  Episode terminated by environment. Resetting...")
                obs, info = env.reset()
                print(f"  Observation after reset: {obs[0]:.2f} HP%, {obs[1]:.2f} MP%, Target: {obs[2]}, Monsters: {obs[3]}, Attacked: {obs[4]}, Pos: ({obs[5]},{obs[6]},{obs[7]})")

        env.close()
        # globals()['execute_action'] = original_execute_action # Restore original
    else:
        print("Skipping conceptual test as critical AI modules were not loaded.")
