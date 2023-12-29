from src.IBallActionGenerator import BallActionGenerator
from src.IAgent import IAgent
import service_pb2 as pb2
import pyrusgeom.soccer_math as smath
from pyrusgeom.soccer_math import *
from pyrusgeom.geom_2d import *
from src.Tools import Tools
from src.IBallAction import IBallAction, ActionType
from src.RawPass import RawDirectPass, RawLeadPass


class GeneratorPass(BallActionGenerator):
    def __init__(self):
        super().__init__()
        self.receivers: pb2.TeammateMessage = []
        self.index = 0
        
    def generate(self, agent: IAgent, init_index: int = 0):
        self.candidateActions = []
        self.receivers = []
        self.debug_list = []
        self.index = init_index
        self.update_receiver(agent)
        self.generate_pass(agent)
        if agent.debug_mode:
            self.log_debug(agent, pb2.LoggerLevel.PASS)
        return self.candidateActions
    
    def update_receiver(self, agent: IAgent):
        if agent.debug_mode:
            agent.add_log_text(pb2.LoggerLevel.PASS, "update_receiver")
        for tm in agent.wm.teammates:
            if tm.uniform_number == agent.wm.self.uniform_number:
                if agent.debug_mode:
                    agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} is me")
                continue
            if tm.uniform_number < 0:
                if agent.debug_mode:
                    agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} unum is less than 0")
                continue
            
            if tm.pos_count > 10:
                if agent.debug_mode:
                    agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} pos_count is more than 10")
                continue
            
            if tm.is_tackling:
                if agent.debug_mode:
                    agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} is tackling")
                continue
            
            if tm.position.x > agent.wm.offside_line_x:
                if agent.debug_mode:
                    agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} is offside")
                continue
            
            if tm.is_goalie and tm.position.x < -30: # todo server param ourPenaltyAreaLineX
                if agent.debug_mode:
                    agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} is goalie and in danger area")
                continue
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"-- {tm.uniform_number} is ok")
            self.receivers.append(tm)
        
    def generate_pass(self, agent: IAgent):
        if agent.debug_mode:
            agent.add_log_text(pb2.LoggerLevel.PASS, "generate_pass")
        for tm in self.receivers:
            self.generate_direct_pass(agent, tm)
        for tm in self.receivers:
            self.generate_lead_pass(agent, tm)
            
    def generate_direct_pass(self, agent: IAgent, tm: pb2.Player):
        if agent.debug_mode:
            agent.add_log_text(pb2.LoggerLevel.PASS, f">> generate_direct_pass to {tm.uniform_number}")
        sp = agent.serverParams
        player_type: pb2.PlayerType = agent.get_type(tm.type_id)
        min_receive_step = 3
        max_direct_pass_dist = 0.8 * smath.inertia_final_distance(sp.ball_speed_max, sp.ball_decay)
        max_receive_ball_speed = sp.ball_speed_max * pow(sp.ball_decay, min_receive_step)
        min_direct_pass_dist = player_type.kickable_area * 2.2
        tm_pos = Vector2D(tm.position.x, tm.position.y)
        tm_vel = Vector2D(tm.velocity.x, tm.velocity.y)
        ball_pos = Vector2D(agent.wm.ball.position.x, agent.wm.ball.position.y)
        if tm_pos.x() > sp.pitch_half_length - 1.5 \
                or tm_pos.x() < -sp.pitch_half_length + 5.0 \
                or tm_pos.abs_y() > sp.pitch_half_width - 1.5:
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED tm_pos is out of field")
            return
        # TODO sp.ourTeamGoalPos()
        if tm_pos.x() < agent.wm.ball.position.x + 1.0 \
                and tm_pos.dist(Vector2D(-52.5, 0)) < 18.0:
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED tm_pos is near our goal")
            return

        max_ball_speed = agent.wm.self.kick_rate * sp.max_power
        if agent.wm.game_mode_type == pb2.GameModeType.PlayOn:
            max_ball_speed = sp.ball_speed_max

        # TODO SP.defaultRealSpeedMax()
        min_ball_speed = 1.0

        receive_point = Tools.inertia_final_point(player_type, tm_pos, tm_vel)
        ball_move_dist = ball_pos.dist(receive_point)

        if ball_move_dist < min_direct_pass_dist or max_direct_pass_dist < ball_move_dist:
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED ball_move_dist is out of range")
            return

        if agent.wm.game_mode_type == pb2.GameModeType.GoalKick_ \
                and receive_point.x() < sp.our_penalty_area_line_x + 1.0 \
                and receive_point.abs_y() < sp.penalty_area_half_width + 1.0:
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED receive_point is in penalty area in goal kick mode")
            return

        max_receive_ball_speed = min(max_receive_ball_speed, player_type.kickable_area + (
                    sp.max_dash_power * player_type.dash_power_rate * player_type.effort_max) * 1.8)
        min_receive_ball_speed = player_type.real_speed_max

        ball_move_angle = (receive_point - ball_pos).th()

        min_ball_step = Tools.ball_move_step(sp.ball_speed_max, ball_move_dist, sp.ball_decay)
        # TODO Penalty step
        start_step = max(max(min_receive_step, min_ball_step), 0)
        max_step = start_step + 2
        if agent.debug_mode:
            agent.add_log_text(pb2.LoggerLevel.PASS, f">>>> DPass to {tm.uniform_number} ({round(tm_pos.x(), 2)}, {round(tm_pos.y(), 2)}) -> ({round(receive_point.x(), 2)}, {round(receive_point.y(), 2)}) start_step: {start_step}, max_step: {max_step}")

        new_pass = RawDirectPass(agent, tm, receive_point,
                start_step, max_step, min_ball_speed,
                max_ball_speed, min_receive_ball_speed,
                max_receive_ball_speed, ball_move_dist,
                ball_move_angle, self.index)
        self.candidateActions.append(new_pass)
    
    def generate_lead_pass(self, agent: IAgent, tm: pb2.Player):
        if agent.debug_mode:
            agent.add_log_text(pb2.LoggerLevel.PASS, f">> generate_lead_pass to {tm.uniform_number}")
        sp = agent.serverParams
        our_goal_dist_thr2 = pow(16.0, 2)
        min_receive_step = 4
        max_receive_step = 20
        min_leading_pass_dist = 3.0
        max_leading_pass_dist = 0.8 * smath.inertia_final_distance(sp.ball_speed_max, sp.ball_decay)
        max_receive_ball_speed = sp.ball_speed_max * pow(sp.ball_decay, min_receive_step)

        max_player_distance = 35
        tm_pos = Vector2D(tm.position.x, tm.position.y)
        tm_vel = Vector2D(tm.velocity.x, tm.velocity.y)
        ball_pos = Vector2D(agent.wm.ball.position.x, agent.wm.ball.position.y)
        ball_vel = Vector2D(agent.wm.ball.velocity.x, agent.wm.ball.velocity.y)
        
        if tm_pos.dist(ball_pos) > max_player_distance:
            if agent.debug_mode:
                agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED tm_pos is too far")
            return

        abgle_divs = 8
        angle_step = 360.0 / abgle_divs
        dist_divs = 4
        dist_step = 1.1

        ptype = agent.get_type(tm.type_id)
        max_ball_speed = agent.wm.self.kick_rate * sp.max_power
        if agent.wm.game_mode_type == pb2.GameModeType.PlayOn:
            max_ball_speed = sp.ball_speed_max
        min_ball_speed = agent.get_type(0).real_speed_max

        max_receive_ball_speed = min(max_receive_ball_speed, ptype.kickable_area + (
                    sp.max_dash_power * ptype.dash_power_rate * ptype.effort_max) * 1.5)
        min_receive_ball_speed = 0.001

        our_goal = Vector2D(-52.5, 0)

        angle_from_ball = (tm_pos - ball_pos).th()
        for d in range(1, dist_divs + 1):
            player_move_dist = dist_step * d
            a_step = 2 if player_move_dist * 2.0 * math.pi / abgle_divs < 0.6 else 1
            for a in range(abgle_divs + 1):
                angle = angle_from_ball + angle_step * a
                receive_point = tm_pos + tm_vel + Vector2D.from_polar(player_move_dist, angle)

                if receive_point.x() > sp.pitch_half_length - 3.0 \
                        or receive_point.x() < -sp.pitch_half_length + 5.0 \
                        or receive_point.abs_y() > sp.pitch_half_width - 3.0:
                    if agent.debug_mode:
                        agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED receive_point is out of field")
                    continue

                if receive_point.x() < ball_pos.x() \
                        and receive_point.dist2(our_goal) < our_goal_dist_thr2:
                    if agent.debug_mode:
                        agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED receive_point is near our goal")
                    continue

                if agent.wm.game_mode_type == pb2.GameModeType.GoalKick_ \
                        and receive_point.x() < sp.our_penalty_area_line_x + 1.0 \
                        and receive_point.abs_y() < sp.penalty_area_half_width + 1.0:
                    if agent.debug_mode:
                        agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED receive_point is in penalty area in goal kick mode")
                    return

                ball_move_dist = ball_pos.dist(receive_point)

                if ball_move_dist < min_leading_pass_dist or max_leading_pass_dist < ball_move_dist:
                    if agent.debug_mode:
                        agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED ball_move_dist is out of range")
                    continue

                nearest_receiver = Tools.get_nearest_teammate(agent, receive_point)
                if nearest_receiver.uniform_number != tm.uniform_number:
                    if agent.debug_mode:
                        agent.add_log_text(pb2.LoggerLevel.PASS, f"## FAILED nearest_receiver is not tm")
                    continue

                new_pass = RawLeadPass(agent, tm, receive_point,
                        min_ball_speed,
                        max_ball_speed, min_receive_ball_speed,
                        max_receive_ball_speed, ball_move_dist,
                        self.index)
                self.candidateActions.append(new_pass)
                


    