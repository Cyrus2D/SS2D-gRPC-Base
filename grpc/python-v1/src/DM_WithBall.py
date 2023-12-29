# from pyparsing import col
import service_pb2 as pb2
from src.IDecisionMaker import IDecisionMaker
from src.IAgent import IAgent
from pyrusgeom.soccer_math import *
from pyrusgeom.geom_2d import *
from src.GEN_Pass import GeneratorPass
from src.RawPass import RawPass


class WithBallDecisionMaker(IDecisionMaker):
    def __init__(self):
        self.pass_generator = GeneratorPass()
        pass

    def make_decision(self, agent: IAgent):
        candidate_actions: list[RawPass] = self.pass_generator.generate(agent, 0)
        candidate_actions.sort(key=lambda x: x.score, reverse=True)
        # TaskManager.run_tasks(candidate_actions, lambda x: x.check())
        for action in candidate_actions:
            action.check()
            if action.get_result() is not None \
                and not action.is_failed():
                
                best_action = action.get_result()
                agent.add_action(pb2.Action(body_smart_kick=pb2.Body_SmartKick(
                    target_point=pb2.Vector2D(x=best_action.targetBallPos.x(), y=best_action.targetBallPos.y()),
                    first_speed=best_action.firstVelocity.r(),
                    first_speed_threshold=0.0,
                    max_steps=best_action.targetCycle)))
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
