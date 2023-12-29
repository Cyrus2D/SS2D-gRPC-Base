from .IBallAction import IBallAction
import service_pb2 as pb2
from src.IAgent import IAgent
from pyrusgeom.vector_2d import Vector2D
from pyrusgeom.angle_deg import AngleDeg
from pyrusgeom.line_2d import Line2D
from src.Tools import Tools
import pyrusgeom.soccer_math as smath
from src.IBallAction import IBallAction, ActionType


class RawPass:
    def check(self):
        pass
    
    def evaluate(self) -> float:
        pass
    
    def get_result(self) -> IBallAction:
        pass
    
    def is_failed(self) -> bool:
        pass

class RawDirectPass(RawPass):
    def __init__(self, 
                agent: IAgent, 
                receiver: pb2.Player, 
                receive_point: Vector2D,
                min_step, 
                max_step, 
                min_first_ball_speed, 
                max_first_ball_speed,
                min_receive_ball_speed, 
                max_receive_ball_speed,
                ball_move_dist, 
                ball_move_angle: AngleDeg, 
                index):
        self.agent = agent
        self.receiver = receiver
        self.receive_point = receive_point
        self.min_step = min_step
        self.max_step = max_step
        self.min_first_ball_speed = min_first_ball_speed
        self.max_first_ball_speed = max_first_ball_speed
        self.min_receive_ball_speed = min_receive_ball_speed
        self.max_receive_ball_speed = max_receive_ball_speed
        self.ball_move_dist = ball_move_dist
        self.ball_move_angle = ball_move_angle
        self.index = index
        self.debug_list = []
        self.failed = False
        self.result: IBallAction = None
        self.score: float = 0.0
        self.evaluate()
        
    def is_failed(self) -> bool:
        return self.failed
    
    def get_result(self) -> IBallAction:
        return self.result
    
    def evaluate(self) -> float:
        self.score = self.receive_point.x()
        goal_dist = self.receive_point.dist(Vector2D(52.5, 0.0))
        if goal_dist < 40.0:
            self.score += (40.0 - goal_dist)
        
    
    def check(self):
        sp = self.agent.serverParams
        ball_pos = Tools.vector2d_message_to_vector2d(self.agent.wm.ball.position)
        same_index = -1
        for step in range(self.min_step, self.max_step + 1):
            same_index += 1
            if self.agent.debug_mode:
                self.agent.add_log_text(pb2.LoggerLevel.PASS, f">>>>>> #{self.index} Pass to {self.receiver.uniform_number} ({round(self.receive_point.x(), 2)}, {round(self.receive_point.y(), 2)}), step:{step}")
            self.index += 1
            first_ball_speed = smath.calc_first_term_geom_series(self.ball_move_dist, sp.ball_decay, step)

            if first_ball_speed < self.min_first_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} ? first ball speed is low")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                break

            if self.max_first_ball_speed < first_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} ? first ball speed is high")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                continue

            receive_ball_speed = first_ball_speed * pow(sp.ball_decay, step)

            if receive_ball_speed < self.min_receive_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} ? receive ball speed is low")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                break

            if self.max_receive_ball_speed < receive_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} ? receive ball speed is high")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                continue

            kick_count = Tools.predict_kick_count(self.agent, self.agent.wm.self.uniform_number, first_ball_speed, self.ball_move_angle)

            o_step, o_unum, o_intercepted_pos = self.predict_opponents_reach_step(self.agent, ball_pos,
                                                                                  first_ball_speed, self.ball_move_angle,
                                                                                  self.receive_point, step + (kick_count - 1) + 5)

            if o_step <= step + (kick_count - 1):
                self.failed = True
            if self.failed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### Failed to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} opp {o_unum} step {o_step} max_step {self.max_step} ? opp reach step is low")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                break
            if self.agent.debug_mode:
                self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### OK to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} opp {o_unum} step {o_step}, max_step {self.max_step}")
            self.debug_list.append((self.index, self.receive_point, True, same_index))
            
            self.result = IBallAction()
            self.result.actionType = ActionType.DIRECT_PASS
            self.result.initBallPos = ball_pos
            self.result.targetBallPos = self.receive_point
            self.result.targetUnum = self.receiver.uniform_number
            self.result.firstVelocity = Vector2D.polar2vector(first_ball_speed, self.ball_move_angle)
            self.result.evaluate()

            find_another_pass = False
            if not find_another_pass:
                break

            if o_step <= step + 3:
                break

            if self.min_step + 3 <= step:
                break
        
    def predict_opponents_reach_step(self, 
                                    agent: IAgent,
                                    first_ball_pos: Vector2D,
                                    first_ball_speed,
                                    ball_move_angle: AngleDeg,
                                    receive_point: Vector2D,
                                    max_cycle):
        first_ball_vel = Vector2D.polar2vector(first_ball_speed, ball_move_angle)
        min_step = 1000
        min_opp = 0
        intercepted_pos = None
        for opp in agent.wm.opponents:
            if opp is None or opp.uniform_number == 0:
                continue
            step, intercepted_pos = Tools.predict_opponent_reach_step(agent, opp, first_ball_pos, first_ball_vel, ball_move_angle,
                                                                        receive_point, max_cycle, 'D')
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"------ Opp {opp.uniform_number} step {step} min_step {min_step} in {intercepted_pos}")
            if step < min_step:
                min_step = step
                min_opp = opp.uniform_number
        return min_step, min_opp, intercepted_pos

class RawLeadPass(RawPass):
    def __init__(self, 
                agent: IAgent, 
                receiver: pb2.Player, 
                receive_point: Vector2D,
                min_first_ball_speed, 
                max_first_ball_speed,
                min_receive_ball_speed, 
                max_receive_ball_speed,
                ball_move_dist, 
                index):
        self.agent = agent
        self.receiver = receiver
        self.receive_point = receive_point
        self.min_step = 0
        self.min_first_ball_speed = min_first_ball_speed
        self.max_first_ball_speed = max_first_ball_speed
        self.min_receive_ball_speed = min_receive_ball_speed
        self.max_receive_ball_speed = max_receive_ball_speed
        self.ball_move_dist = ball_move_dist
        self.index = index
        self.debug_list = []
        self.failed = False
        self.result: IBallAction = None
        self.score: float = 0.0
        self.evaluate()
        
    def is_failed(self) -> bool:
        return self.failed
    
    def get_result(self) -> IBallAction:
        return self.result   

    def evaluate(self) -> float:
        self.score = self.receive_point.x()
        goal_dist = self.receive_point.dist(Vector2D(52.5, 0.0))
        if goal_dist < 40.0:
            self.score += (40.0 - goal_dist)
        
    
    def check(self):
        min_receive_step = 4
        max_receive_step = 20

        sp = self.agent.serverParams
        ball_pos = Tools.vector2d_message_to_vector2d(self.agent.wm.ball.position)
        tm_pos = Vector2D(self.receiver.position.x, self.receiver.position.y)
        ball_move_line = Line2D(ball_pos, self.receive_point)
        player_line_dist = ball_move_line.dist(tm_pos)
        move_dist_penalty_step = int(player_line_dist * 0.3)
        receiver_step = self.predict_receiver_reach_step(self.agent, self.receiver, self.receive_point, 'L') + move_dist_penalty_step
        ball_move_angle = (self.receive_point - ball_pos).th()

        min_ball_step = Tools.ball_move_step(sp.ball_speed_max, self.ball_move_dist, sp.ball_decay)

        start_step = max(max(min_receive_step, min_ball_step), receiver_step)
        max_step = max(max_receive_step, start_step + 3)
        max_step = start_step + 3
        self.min_step = start_step
        
        sp = self.agent.serverParams
        same_index = -1
        for step in range(self.min_step, max_step + 1):
            same_index += 1
            if self.agent.debug_mode:
                self.agent.add_log_text(pb2.LoggerLevel.PASS, f">>>>>> #{self.index} Pass to {self.receiver.uniform_number} ({round(self.receive_point.x(), 2)}, {round(self.receive_point.y(), 2)}), step:{step}")
            self.index += 1
            first_ball_speed = smath.calc_first_term_geom_series(self.ball_move_dist, sp.ball_decay, step)

            if first_ball_speed < self.min_first_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} ? first ball speed is low")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                break

            if self.max_first_ball_speed < first_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} ? first ball speed is high")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                continue

            receive_ball_speed = first_ball_speed * pow(sp.ball_decay, step)

            if receive_ball_speed < self.min_receive_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} ? receive ball speed is low")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                break

            if self.max_receive_ball_speed < receive_ball_speed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### FAILED to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} ? receive ball speed is high")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                continue

            kick_count = Tools.predict_kick_count(self.agent, self.agent.wm.self.uniform_number, first_ball_speed, ball_move_angle)

            o_step, o_unum, o_intercepted_pos = self.predict_opponents_reach_step(self.agent, ball_pos,
                                                                                  first_ball_speed, ball_move_angle,
                                                                                  self.receive_point, step + (kick_count - 1) + 5)

            if o_step <= step + (kick_count - 1):
                self.failed = True
            if self.failed:
                if self.agent.debug_mode:
                    self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### Failed to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} opp {o_unum} step {o_step} max_step {max_step} ? opp reach step is low")
                self.debug_list.append((self.index, self.receive_point, False, same_index))
                break
            if self.agent.debug_mode:
                self.agent.add_log_text(pb2.LoggerLevel.PASS, f"###### OK to {self.receiver.uniform_number} step:{step} ball_speed:{first_ball_speed} rball_speed:{receive_ball_speed} opp {o_unum} step {o_step}, max_step {max_step}")
            self.debug_list.append((self.index, self.receive_point, True, same_index))
            
            self.result = IBallAction()
            self.result.actionType = ActionType.DIRECT_PASS
            self.result.initBallPos = ball_pos
            self.result.targetBallPos = self.receive_point
            self.result.targetUnum = self.receiver.uniform_number
            self.result.firstVelocity = Vector2D.polar2vector(first_ball_speed, ball_move_angle)
            self.result.evaluate()

            find_another_pass = False
            if not find_another_pass:
                break

            if o_step <= step + 3:
                break

            if self.min_step + 3 <= step:
                break

    def predict_receiver_reach_step(self, agent: IAgent, receiver: pb2.Player, pos: Vector2D, pass_type):
        ptype = agent.get_type(receiver.type_id)
        receiver_pos = Vector2D(receiver.position.x, receiver.position.y)
        receiver_vel = Vector2D(receiver.velocity.x, receiver.velocity.y)
        receiver_inertia_pos = receiver_pos + receiver_vel
        target_dist = receiver_inertia_pos.dist(pos)
        n_turn = 1 if receiver.body_direction_count > 0 else Tools.predict_player_turn_cycle(agent.serverParams, ptype, receiver.body_direction,
                                                                                             receiver_vel.r(), target_dist, 
                                                                                             (pos - receiver_inertia_pos).th(),
                                                                                             ptype.kickable_area, False)
        dash_dist = target_dist

        # if use_penalty:
        #     dash_dist += receiver.penalty_distance_;

        if pass_type == 'L':
            dash_dist *= 1.05

            dash_angle = (pos - receiver_pos).th()

            if dash_angle.abs() > 90.0 or receiver.body_direction_count > 1 or (dash_angle - AngleDeg(receiver.body_direction)).abs() > 30.0:
                n_turn += 1

        
        n_dash = Tools.cycles_to_reach_distance(dash_dist, ptype.real_speed_max)

        n_step = n_turn + n_dash if n_turn == 0 else n_turn + n_dash + 1
        return n_step
        
    def predict_opponents_reach_step(self, 
                                    agent: IAgent,
                                    first_ball_pos: Vector2D,
                                    first_ball_speed,
                                    ball_move_angle: AngleDeg,
                                    receive_point: Vector2D,
                                    max_cycle):
        first_ball_vel = Vector2D.polar2vector(first_ball_speed, ball_move_angle)
        min_step = 1000
        min_opp = 0
        intercepted_pos = None
        for opp in agent.wm.opponents:
            if opp is None or opp.uniform_number == 0:
                continue
            step, intercepted_pos = Tools.predict_opponent_reach_step(agent, opp, first_ball_pos, first_ball_vel, ball_move_angle,
                                                                        receive_point, max_cycle, 'L')
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"------ Opp {opp.uniform_number} step {step} min_step {min_step} in {intercepted_pos}")
            if step < min_step:
                min_step = step
                min_opp = opp.uniform_number
        return min_step, min_opp, intercepted_pos
