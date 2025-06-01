import pyautogui
from time import sleep, time
import traceback
import sys
import copy
import random
from src.ai.observation import extract_observation
from src.ai.actions import Action, execute_action
from src.ai.reward import calculate_reward
from src.gameplay.cavebot import resolveCavebotTasks, shouldAskForCavebotTasks
from src.gameplay.combo import comboSpells
from src.gameplay.core.middlewares.battleList import setBattleListMiddleware
from src.gameplay.core.middlewares.chat import setChatTabsMiddleware
from src.gameplay.core.middlewares.gameWindow import setDirectionMiddleware, setGameWindowCreaturesMiddleware, setGameWindowMiddleware, setHandleLootMiddleware
from src.gameplay.core.middlewares.playerStatus import setMapPlayerStatusMiddleware
from src.gameplay.core.middlewares.statsBar import setMapStatsBarMiddleware
from src.gameplay.core.middlewares.radar import setRadarMiddleware, setWaypointIndexMiddleware
from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware
from src.gameplay.core.middlewares.tasks import setCleanUpTasksMiddleware
from src.gameplay.core.tasks.lootCorpse import LootCorpseTask
from src.gameplay.resolvers import resolveTasksByWaypoint
from src.gameplay.healing.observers.eatFood import eatFood
from src.gameplay.healing.observers.autoHur import autoHur
from src.gameplay.healing.observers.clearPoison import clearPoison
from src.gameplay.healing.observers.healingBySpells import healingBySpells
from src.gameplay.healing.observers.healingByPotions import healingByPotions
from src.gameplay.healing.observers.healingByMana import healingByMana
from src.gameplay.healing.observers.swapAmulet import swapAmulet
from src.gameplay.healing.observers.swapRing import swapRing
from src.gameplay.targeting import hasCreaturesToAttack
from src.repositories.gameWindow.creatures import getClosestCreature, getTargetCreature

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

class LegacyGameLoopThread:
    # TODO: add typings
    def __init__(self, context):
        self.context = context

    def mainloop(self):
        while True:
            try:
                if self.context.context['py_pause']:
                    sleep(1)
                    continue
                startTime = time()
                self._run_perception_step()

                # Original scripted logic (currently commented out for AI control)
                # self.context.context = self.handleGameplayTasks(
                #     self.context.context)
                # self.context.context = self.context.context['py_tasksOrchestrator'].do(
                #     self.context.context)
                # self.context.context['py_radar']['lastCoordinateVisited'] = self.context.context['py_radar']['coordinate']
                # healingByPotions(self.context.context)
                # healingByMana(self.context.context)
                # healingBySpells(self.context.context)
                # comboSpells(self.context.context)
                # swapAmulet(self.context.context)
                # swapRing(self.context.context)
                # clearPoison(self.context.context)
                # autoHur(self.context.context)
                # eatFood(self.context.context)

                endTime = time()
                diff = endTime - startTime
                sleep(max(0.045 - diff, 0))
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                print(f"An exception occurred: {e}")
                print(traceback.format_exc())

    def _run_perception_step(self):
        """
        Runs a single step of game perception, updating the context.
        This includes screenshot capture, radar, battle list, game window,
        player status, and other middleware processing.
        """
        # Renamed context to self.context.context to match access patterns elsewhere in the class
        current_context = self.context.context
        if current_context['py_pause']:
            return
        current_context = setScreenshotMiddleware(current_context)
        current_context = setRadarMiddleware(current_context)
        current_context = setChatTabsMiddleware(current_context)
        current_context = setBattleListMiddleware(current_context)
        current_context = setGameWindowMiddleware(current_context)
        current_context = setDirectionMiddleware(current_context)
        current_context = setGameWindowCreaturesMiddleware(current_context)
        if current_context['py_cave']['enabled'] and current_context['py_cave']['runToCreatures'] == True:
            current_context = setHandleLootMiddleware(current_context)
        else:
            current_context['py_cave']['targetCreature'] = getTargetCreature(current_context['gameWindow']['monsters'])
        current_context = setWaypointIndexMiddleware(current_context)
        current_context = setMapPlayerStatusMiddleware(current_context)
        current_context = setMapStatsBarMiddleware(current_context)
        current_context = setCleanUpTasksMiddleware(current_context)
        self.context.context = current_context # Ensure the main context reference is updated

    def handleGameData(self, context_param): # Parameter name changed to avoid confusion with self.context.context
        # This method now calls the new perception step method.
        # The passed 'context_param' is effectively ignored if self.context.context is the true source of state.
        # However, to maintain the original signature and behavior if it were called externally with a dict:
        if context_param['py_pause']:
             return context_param
        self.context.context = context_param # Make sure we're operating on the passed context if this is intended
        self._run_perception_step()
        return self.context.context # Return the context as original handleGameData did

    def handleGameplayTasks(self, context):
        # TODO: func to check if coord is none
        if context['py_radar']['coordinate'] is None:
            return context
        if any(coord is None for coord in context['py_radar']['coordinate']):
            return context
        context['py_cave']['closestCreature'] = getClosestCreature(
            context['gameWindow']['monsters'], context['py_radar']['coordinate'])
        currentTask = context['py_tasksOrchestrator'].getCurrentTask(context)
        if currentTask is not None and currentTask.name == 'selectChatTab':
            return context
        if len(context['loot']['corpsesToLoot']) > 0 and context['py_cave']['runToCreatures'] == True and context['py_cave']['enabled']:
            context['way'] = 'lootCorpses'
            if currentTask is not None and currentTask.rootTask is not None and currentTask.rootTask.name != 'lootCorpse':
                context['py_tasksOrchestrator'].setRootTask(context, None)
            if context['py_tasksOrchestrator'].getCurrentTask(context) is None:
                # TODO: get closest dead corpse
                firstDeadCorpse = context['loot']['corpsesToLoot'][0]
                context['py_tasksOrchestrator'].setRootTask(
                    context, LootCorpseTask(firstDeadCorpse))
            context['gameWindow']['previousMonsters'] = context['gameWindow']['monsters']
            return context
        if context['py_cave']['runToCreatures'] == True and context['py_cave']['enabled']:
            hasCreaturesToAttackAfterCheck = hasCreaturesToAttack(context)
            if hasCreaturesToAttackAfterCheck:
                if context['py_cave']['closestCreature'] is not None:
                    context['way'] = 'py_cave'
                else:
                    context['way'] = 'waypoint'
            else:
                context['way'] = 'waypoint'
            if hasCreaturesToAttackAfterCheck and shouldAskForCavebotTasks(context):
                currentRootTask = currentTask.rootTask if currentTask is not None else None
                isTryingToAttackClosestCreature = currentRootTask is not None and (
                    currentRootTask.name == 'attackClosestCreature')
                if not isTryingToAttackClosestCreature:
                    context = resolveCavebotTasks(context)
            elif context['way'] == 'waypoint':
                if context['py_tasksOrchestrator'].getCurrentTask(context) is None:
                    currentWaypointIndex = context['py_cave']['waypoints']['currentIndex']
                    currentWaypoint = context['py_cave']['waypoints']['items'][currentWaypointIndex]
                    context['py_tasksOrchestrator'].setRootTask(
                        context, resolveTasksByWaypoint(currentWaypoint))
        elif context['py_cave']['enabled'] and context['py_tasksOrchestrator'].getCurrentTask(context) is None:
                currentWaypointIndex = context['py_cave']['waypoints']['currentIndex']
                if currentWaypointIndex is not None:
                    currentWaypoint = context['py_cave']['waypoints']['items'][currentWaypointIndex]
                    context['py_tasksOrchestrator'].setRootTask(
                        context, resolveTasksByWaypoint(currentWaypoint))

        context['gameWindow']['previousMonsters'] = context['gameWindow']['monsters']
        return context
