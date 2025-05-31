from typing import Dict, Any
# Assuming src.ai.actions will exist and Action enum can be imported
try:
    from src.ai.actions import Action
except ImportError:
    print("Warning: src.ai.actions could not be imported. Action enum will not be available for reward calculation specifics.")
    # Define a dummy Action class if import fails, so the rest of the script can be parsed
    class Action: # type: ignore
        DO_NOTHING = 0

def calculate_reward(previous_context: Dict[str, Any],
                     current_context: Dict[str, Any],
                     action_id: int) -> float:
    """
    Calculates a reward based on the change between previous_context and current_context,
    and the action taken.
    """
    reward = 0.0

    # --- HP Change Reward ---
    prev_hp = previous_context.get('ng_statusBar', {}).get('hpPercentage', 0.0)
    if prev_hp is None: prev_hp = 0.0 # Ensure None is handled
    curr_hp = current_context.get('ng_statusBar', {}).get('hpPercentage', 0.0)
    if curr_hp is None: curr_hp = 0.0 # Ensure None is handled

    hp_change = curr_hp - prev_hp
    # Scaled reward: e.g., losing 10% HP is -10 reward, gaining 5% is +5.
    hp_reward = hp_change * 100
    reward += hp_reward

    # --- Target Disappeared Reward (Proxy for Kill) ---
    # Condition: Was previously targeting and attacking a creature, and now is not (and no new immediate target).
    prev_target_creature = previous_context.get('ng_cave', {}).get('targetCreature')
    prev_is_attacking = previous_context.get('ng_cave', {}).get('isAttackingSomeCreature', False)
    prev_had_target_and_attacking = prev_target_creature is not None and prev_is_attacking

    curr_target_creature = current_context.get('ng_cave', {}).get('targetCreature')
    curr_is_attacking = current_context.get('ng_cave', {}).get('isAttackingSomeCreature', False)
    # Current state implies no combat engagement with a specific target.
    curr_has_no_target_and_not_attacking = curr_target_creature is None and not curr_is_attacking

    if prev_had_target_and_attacking and curr_has_no_target_and_not_attacking:
        # Further check: was the *specific* previous target killed?
        # This is harder without IDing creatures. The current logic is a simpler proxy:
        # if combat stops and there's no immediate new target, assume the previous one was dealt with.
        kill_reward = 50.0  # Significant positive reward for a "kill"
        reward += kill_reward

    # --- Action Penalty/Liveness ---
    # Small penalty for doing nothing, small reward for taking any action.
    # This encourages exploration if no other rewards are being achieved.
    try:
        action_taken = Action(action_id)
        if action_taken == Action.DO_NOTHING:
            reward -= 0.5 # Slightly larger penalty for inaction
        else:
            reward += 0.1 # Small incentive to do *something*
    except (NameError, ValueError): # Handles if Action enum isn't available or invalid action_id
        # If Action enum is not available, we can't apply action-specific rewards/penalties easily.
        # Or, if action_id is somehow out of Action's defined range.
        pass


    # --- Death Penalty (Dominating Negative Reward) ---
    if curr_hp == 0.0 and prev_hp > 0.0: # Died in this step
        death_penalty = -500.0
        reward += death_penalty
        # Optional: print("DEBUG: Death penalty applied.")

    return reward

# Example Usage:
if __name__ == '__main__':
    # Dummy contexts for testing
    context_hp_full_no_target = {
        'ng_statusBar': {'hpPercentage': 1.0},
        'ng_cave': {'targetCreature': None, 'isAttackingSomeCreature': False}
    }
    context_hp_low_no_target = {
        'ng_statusBar': {'hpPercentage': 0.2},
        'ng_cave': {'targetCreature': None, 'isAttackingSomeCreature': False}
    }
    context_hp_mid_with_target_attacking = {
        'ng_statusBar': {'hpPercentage': 0.6},
        'ng_cave': {'targetCreature': {'name': 'Dragon'}, 'isAttackingSomeCreature': True}
    }
    context_dead = {
        'ng_statusBar': {'hpPercentage': 0.0},
        'ng_cave': {'targetCreature': None, 'isAttackingSomeCreature': False}
    }

    # Test 1: Took damage
    r1 = calculate_reward(context_hp_full_no_target, context_hp_low_no_target, Action.DO_NOTHING)
    print(f"Test 1 (Took damage, did nothing): Reward = {r1}") # Expected: (0.2-1.0)*100 - 0.5 = -80.5

    # Test 2: Killed a target (target disappeared, was attacking, now not)
    r2 = calculate_reward(context_hp_mid_with_target_attacking, context_hp_full_no_target, Action.PRESS_ATTACK_HOTKEY)
    # Expected: (1.0-0.6)*100 (hp gain) + 50 (kill) + 0.05 (action) = 40 + 50 + 0.1 = 90.1
    print(f"Test 2 (Killed target, HP recovered): Reward = {r2}")

    # Test 3: Died
    r3 = calculate_reward(context_hp_low_no_target, context_dead, Action.DO_NOTHING)
    print(f"Test 3 (Died, did nothing): Reward = {r3}") # Expected: (0.0-0.2)*100 - 500 - 0.5 = -20 - 500 - 0.5 = -520.5

    # Test 4: Used a potion and healed
    context_hp_mid_healed_to_full = {
        'ng_statusBar': {'hpPercentage': 1.0},
        'ng_cave': {'targetCreature': None, 'isAttackingSomeCreature': False}
    }
    r4 = calculate_reward(context_hp_low_no_target, context_hp_mid_healed_to_full, Action.USE_HEALTH_POTION)
    print(f"Test 4 (Used potion, healed): Reward = {r4}") # Expected: (1.0-0.2)*100 + 0.1 = 80.1

    # Test 5: Did nothing, no change
    r5 = calculate_reward(context_hp_full_no_target, context_hp_full_no_target, Action.DO_NOTHING)
    print(f"Test 5 (Did nothing, no change): Reward = {r5}") # Expected: 0 - 0.5 = -0.5

    # Test 6: Attacked, but target still there, took some damage
    context_hp_mid_still_targeting_slight_damage = {
        'ng_statusBar': {'hpPercentage': 0.55}, # from 0.6
        'ng_cave': {'targetCreature': {'name': 'Dragon'}, 'isAttackingSomeCreature': True}
    }
    r6 = calculate_reward(context_hp_mid_with_target_attacking, context_hp_mid_still_targeting_slight_damage, Action.PRESS_ATTACK_HOTKEY)
    print(f"Test 6 (Attacked, target remains, took damage): Reward = {r6}") # Expected: (0.55-0.6)*100 + 0.1 = -5 + 0.1 = -4.9
