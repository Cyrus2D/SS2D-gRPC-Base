# from pyparsing import col
import service_pb2 as pb2
from src.IDecisionMaker import IDecisionMaker
from src.IAgent import IAgent
from pyrusgeom.soccer_math import *
from pyrusgeom.geom_2d import *
from src.GEN_Pass import GeneratorPass
from src.RawPass import RawPass
import multiprocessing as mp
from task_manager import ITask, OldTaskManager, TaskManager

# TODO:
# normal: all
# best_break
# pool: 5, 10

class ActionGroupTask(ITask):
    group_size: int = 10
    
    def __init__(self, actions: list[RawPass]) -> None:
        super().__init__()
        self.actions = actions
    
    def _run(self) -> None:
        for action in self.actions:
            action.check()
    
    def getResult(self):
        return self.actions

# def run_actions_with_task_manager(acttions: list[RawPass]):
#     tm = OldTaskManager(-1, 20, [ActionTask(action) for action in acttions])
#     res = tm.run_tasks()
#     res = list(filter(lambda x: not x.is_failed() and x.get_result() is not None, res))
#     return res[0]

def run_actions_with_pool(acttions: list[RawPass]):
    pool = mp.Pool(10)
    res = pool.map(run_action, acttions)
    res = list(filter(lambda x: x is not None and not x.is_failed() and x.get_result() is not None, res))
    if len(res) == 0:
        return None
    return res[0]

def run_action(action: RawPass):
    action.check()
    return action

class WithBallDecisionMaker(IDecisionMaker):
    def __init__(self):
        self.pass_generator = GeneratorPass()
        self.pool = None

    def make_decision(self, agent: IAgent):
        candidate_actions: list[RawPass] = self.pass_generator.generate(agent, 0)
        
        
        if len(candidate_actions) == 0:
            agent.add_action(pb2.Action(body_hold_ball=pb2.Body_HoldBall()))
            return
        
        candidate_actions.sort(key=lambda x: x.score, reverse=True)
        TaskManager.set_tasks([
            ActionGroupTask(candidate_actions[i:i+ActionGroupTask.group_size])
            for i in range(0, len(candidate_actions), ActionGroupTask.group_size)
        ])
        results = TaskManager.get_results()
        results = [item for sublist in results for item in sublist]
        results = list(filter(lambda x: x is not None and not x.is_failed() and x.get_result() is not None, results))
        if len(results) == 0:
            agent.add_action(pb2.Action(body_hold_ball=pb2.Body_HoldBall()))
            return
        best_action = results[0].get_result()
        print(best_action)
        agent.add_action(pb2.Action(body_smart_kick=pb2.Body_SmartKick(
            target_point=pb2.Vector2D(x=best_action.targetBallPos.x(), y=best_action.targetBallPos.y()),
            first_speed=best_action.firstVelocity.r(),
            first_speed_threshold=0.0,
            max_steps=best_action.targetCycle)))
        # TaskManager.run_tasks(candidate_actions, lambda x: x.check())
        # best_action = None
        # for action in candidate_actions:
        #     action.check()
        #     if action.get_result() is not None \
        #         and not action.is_failed():
                
        #         best_action = action.get_result()
        # if best_action is not None:
        #     agent.add_action(pb2.Action(body_smart_kick=pb2.Body_SmartKick(
        #         target_point=pb2.Vector2D(x=best_action.targetBallPos.x(), y=best_action.targetBallPos.y()),
        #         first_speed=best_action.firstVelocity.r(),
        #         first_speed_threshold=0.0,
        #         max_steps=best_action.targetCycle)))
        # else:
        #     agent.add_action(pb2.Action(body_hold_ball=pb2.Body_HoldBall()))
        return
                

        if len(candidate_actions) == 0:
            agent.add_action(pb2.Action(body_hold_ball=pb2.Body_HoldBall()))
            return

        if agent.debug_mode:
            agent.add_log_text(pb2.LoggerLevel.PASS, f"candidate_actions: {candidate_actions}")
        candidate_actions.sort(key=lambda x: x.score, reverse=True)
        best_action = candidate_actions[0]

        agent.add_action(pb2.Action(body_smart_kick=pb2.Body_SmartKick(
            target_point=pb2.Vector2D(x=best_action.targetBallPos.x(), y=best_action.targetBallPos.y()),
            first_speed=best_action.firstVelocity.r(),
            first_speed_threshold=0.0,
            max_steps=best_action.targetCycle)))
