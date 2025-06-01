import os
import sys

# Ensure the src directory is in the Python path
# This allows the script to be run from the root of the project (e.g., python src/ai/train.py)
# And for imports like `from src.ai.env import TibiaAIEnv` to work directly.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir)) # Assuming src/ai/train.py, so ../../ is project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ai.env import TibiaAIEnv
from src.gameplay.context import context as base_context_dict # The actual context dictionary
from src.ui.context import Context as BotContextManager # The wrapper class from main.py
from src.gameplay.threads.legacy_game_loop import LegacyGameLoopThread

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.env_checker import check_env

def main():
    print("Initializing bot components for AI training...")

    # 1. Initialize bot's context and main loop thread instance
    # This mimics the setup in the root main.py
    # Ensure base_context_dict is a fresh copy if multiple runs are intended in one script exec (not typical for train.py)
    bot_shared_context = base_context_dict
    bot_context_manager_instance = BotContextManager(bot_shared_context)
    game_loop_thread_instance = LegacyGameLoopThread(bot_context_manager_instance)

    print("Initializing Tibia AI Environment...")
    # 2. Instantiate the AI Environment
    # Pass the necessary bot components to the environment
    env = TibiaAIEnv(
        bot_context_manager=bot_context_manager_instance,
        legacy_game_loop_thread_instance=game_loop_thread_instance
    )

    # It's a good practice to check your custom environment
    # Note: This check might be very slow if the environment's step/reset involves actual game interaction with delays.
    # Consider commenting out for faster iteration once confident.
    # print("Checking custom environment...")
    # check_env(env, warn=True) # Disable if too slow or causing issues during setup
    # print("Environment check passed (or warnings issued).")

    # Wrap it in a DummyVecEnv for Stable Baselines3 compatibility
    env = DummyVecEnv([lambda: env])

    # 3. Define the PPO model
    # Log directories
    log_dir = "./training_logs/"
    tensorboard_log_dir = os.path.join(log_dir, "ppo_tibia_tensorboard/")
    best_model_save_path = os.path.join(log_dir, "best_model/")
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(tensorboard_log_dir, exist_ok=True)
    os.makedirs(best_model_save_path, exist_ok=True)

    print(f"Initializing PPO model. TensorBoard logs will be saved to: {tensorboard_log_dir}")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=tensorboard_log_dir,
        n_steps=2048, # Common value, adjust as needed
        batch_size=64, # Common value
        gamma=0.99, # Discount factor
        gae_lambda=0.95,
        # ent_coef=0.0, # Entropy coefficient, adjust if needed
        # vf_coef=0.5, # Value function coefficient
        # learning_rate=2.5e-4, # Adam optimizer learning rate
    )

    # 4. Callbacks (Optional but recommended)
    # Separate eval env (optional, can use the same training env if reset is robust)
    # For simplicity here, we won't create a separate eval_env instance,
    # but it's good practice for more rigorous evaluation.
    # eval_callback = EvalCallback(env, best_model_save_path=best_model_save_path,
    #                              log_path=log_dir, eval_freq=5000, n_eval_episodes=5,
    #                              deterministic=True, render=False)

    # Example of stopping training if a certain reward threshold is met
    # callback_on_best = StopTrainingOnRewardThreshold(reward_threshold=100, verbose=1) # Adjust threshold
    # eval_callback_with_stop = EvalCallback(env, best_model_save_path=best_model_save_path,
    #                                       log_path=log_dir, eval_freq=1000,
    #                                       callback_on_new_best=callback_on_best)


    # 5. Start training
    total_timesteps_to_train = 50000 # Adjust as needed for initial testing
    print(f"Starting training for {total_timesteps_to_train} timesteps...")
    try:
        # model.learn(total_timesteps=total_timesteps_to_train, callback=eval_callback_with_stop)
        model.learn(total_timesteps=total_timesteps_to_train) # Simpler call without eval callback for now
    except KeyboardInterrupt:
        print("Training interrupted by user.")
    finally:
        # 6. Save the trained model
        model_save_path = os.path.join(log_dir, "ppo_tibia_agent_final.zip")
        print(f"Saving final model to: {model_save_path}")
        model.save(model_save_path)
        print("Training complete. Model saved.")

if __name__ == '__main__':
    # Before running, ensure:
    # 1. Tibia client is running and logged in.
    # 2. Arduino is connected and ARDUINO_COM_PORT env var is set if not using default.
    # 3. The game window is visible and configured as the bot expects.
    # 4. Python environment has all dependencies.
    print("=== Tibia AI Training Script ===")
    print("IMPORTANT: Ensure the game client is running, configured, and character is logged in.")
    print("           Set ARDUINO_COM_PORT environment variable if not using default COM33.")
    print("           The bot will take control of mouse/keyboard based on AI actions.")
    print("           Press Ctrl+C in this terminal to interrupt training.")
    # Add a small delay or user confirmation before starting?
    # input("Press Enter to start training (ensure game is ready)...")
    main()

```
