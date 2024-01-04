from pyrusgeom.geom_2d import *
import pyrusgeom.soccer_math as smath
from src.IAgent import IAgent
from src.IBallAction import ActionType, DribbleAction

from src.IBallActionGenerator import BallActionGenerator
from src.Tools import Tools
from service_pb2 import WorldModel

debug_dribble = False
max_dribble_time = 0


class GeneratorDribble(BallActionGenerator):
    def __init__(self):
        super().__init__()
        self.index = 0
        self.candidates = []
    
    def generator(self, agent: IAgent):
        global max_dribble_time
        self.generate_simple_dribble(agent)

        # if debug_dribble:
            # for dribble in self.debug_list:
            #     if dribble[2]:
            #         log.sw_log().dribble().add_message( dribble[1].x(), dribble[1].y(), '{}'.format(dribble[0]))
            #         log.sw_log().dribble().add_circle( cicle=Circle2D(dribble[1], 0.2),
            #                         color=Color(string='green'))
            #     else:
            #         log.sw_log().dribble().add_message( dribble[1].x(), dribble[1].y(), '{}'.format(dribble[0]))
            #         log.sw_log().dribble().add_circle( cicle=Circle2D(dribble[1], 0.2),
            #                         color=Color(string='red'))
        # log.sw_log().dribble().add_text( 'time:{} max is {}'.format(end_time - start_time, max_dribble_time))
        return self.candidates

    def generate_simple_dribble(self, agent: IAgent):
        wm = agent.wm
        angle_div = 16
        angle_step = 360.0 / angle_div

        sp = agent.serverParams
        ptype = agent.get_type(wm.self.type_id)

        my_first_speed = Tools.vector2d_message_to_vector2d(wm.self.velocity).r()

        for a in range(angle_div):
            dash_angle = AngleDeg(wm.self.body_direction + (angle_step * a))

            if wm.self.position.x < 16.0 and dash_angle.abs() > 100.0:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( '#dash angle:{} cancel is not safe1'.format(dash_angle))
                continue

            if wm.self.position.x < -36.0 and abs(wm.self.position.y) < 20.0 and dash_angle.abs() > 45.0:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( '#dash angle:{} cancel is not safe2'.format(dash_angle))
                continue

            n_turn = 0

            my_speed = my_first_speed * ptype.player_decay
            dir_diff = AngleDeg(angle_step * a).abs()

            while dir_diff > 10.0:
                dir_diff -= Tools.effective_turn(sp.max_moment, my_speed, ptype.inertia_moment)
                if dir_diff < 0.0:
                    dir_diff = 0.0
                my_speed *= ptype.player_decay
                n_turn += 1

            if n_turn >= 3:
                continue

            if angle_step * a < 180.0:
                dash_angle -= dir_diff
            else:
                dash_angle += dir_diff
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( '#dash angle:{} turn:{}'.format(dash_angle, n_turn))
            self.simulate_kick_turns_dashes(agent, dash_angle, n_turn)

    def simulate_kick_turns_dashes(self, agent: IAgent, dash_angle, n_turn):
        wm = agent.wm
        
        max_dash = 8
        min_dash = 2

        self_cache = []

        self.create_self_cache(agent, dash_angle, n_turn, max_dash, self_cache)
        # if debug_dribble:
        #     log.sw_log().dribble().add_text( '##self_cache:{}'.format(self_cache))
        sp = agent.serverParams
        ptype = agent.get_type(wm.self.type_id)

        # trap_rel = Vector2D.polar2vector(ptype.playerSize() + ptype.kickableMargin() * 0.2 + SP.ball_size(), dash_angle)
        trap_rel = Vector2D.polar2vector(ptype.player_size + ptype.kickable_margin * 0.2 + 0, dash_angle)

        max_x = sp.pitch_half_length - 1.0
        max_y = sp.pitch_half_width - 1.0
        
        ball_pos = Tools.vector2d_message_to_vector2d(wm.ball.position)
        ball_vel = Tools.vector2d_message_to_vector2d(wm.ball.velocity)

        for n_dash in range(max_dash, min_dash - 1, -1):
            self.index += 1
            ball_trap_pos:Vector2D = self_cache[n_turn + n_dash] + trap_rel

            if ball_trap_pos.abs_x() > max_x or ball_trap_pos.abs_y() > max_y:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   '#index:{} target:{} our of field'.format(self.index, ball_trap_pos))
                    # self.debug_list.append((self.index, ball_trap_pos, False))
                continue

            term = (1.0 - pow(sp.ball_decay, 1 + n_turn + n_dash ) ) / (1.0 - sp.ball_decay)
            first_vel: Vector2D = (ball_trap_pos - ball_pos) / term
            kick_accel: Vector2D = first_vel - ball_vel
            kick_power = kick_accel.r() / wm.self.kick_rate

            if kick_power > sp.max_power or kick_accel.r2() > pow(sp.ball_accel_max, 2) or first_vel.r2() > pow(
                    sp.ball_speed_max, 2):
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   '#index:{} target:{} need more power, power:{}, accel:{}, vel:{}'.format(
                #                       self.index, ball_trap_pos, kick_power, kick_accel, first_vel))
                #     self.debug_list.append((self.index, ball_trap_pos, False))
                continue

            if (ball_pos + first_vel).dist2(self_cache[0]) < pow(ptype.player_size + sp.ball_size + 0.1, 2):
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   '#index:{} target:{} in body, power:{}, accel:{}, vel:{}'.format(
                #                       self.index, ball_trap_pos, kick_power, kick_accel, first_vel))
                # self.debug_list.append((self.index, ball_trap_pos, False))
                continue

            candidate = DribbleAction()
            candidate.actionType = ActionType.DRIBBLE
            candidate.initBallPos = Tools.vector2d_message_to_vector2d(wm.ball.position)
            candidate.targetBallPos = ball_trap_pos
            candidate.targetUnum = wm.self.uniform_number
            candidate.firstVelocity = first_vel
            candidate.index = self.index
            candidate.dribble_steps = n_turn + n_dash + 1
            candidate.n_turn = n_turn
            candidate.n_dash = n_dash
            candidate.evaluate()
            self.candidates.append(candidate)
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   '#index:{} target:{}, power:{}, accel:{}, vel:{} OK'.format(
                #                       self.index, ball_trap_pos, kick_power, kick_accel, first_vel))
                #     self.debug_list.append((self.index, ball_trap_pos, True))
            # else:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   '#index:{} target:{}, power:{}, accel:{}, vel:{} Opponent catch it'.format(
                #                       self.index, ball_trap_pos, kick_power, kick_accel, first_vel))
                #     self.debug_list.append((self.index, ball_trap_pos, False))

    def create_self_cache(self, agent: IAgent, dash_angle, n_turn, n_dash, self_cache):
        wm = agent.wm
        sp = agent.serverParams
        ptype = agent.get_type(wm.self.type_id)

        self_cache.clear()

        # stamina_model = wm.self().stamina_model()

        my_pos = Tools.vector2d_message_to_vector2d(wm.self.position)
        my_vel = Tools.vector2d_message_to_vector2d(wm.self.velocity)

        my_pos += my_vel
        my_vel *= ptype.player_decay

        self_cache.append(Vector2D(my_pos))

        for i in range(n_turn):
            my_pos += my_vel
            my_vel *= ptype.player_decay
            self_cache.append(Vector2D(my_pos))
            # stamina_model.simulate_waits(ptype, 1 + n_turn)

        unit_vec = Vector2D.polar2vector(1.0, dash_angle)

        for i in range(n_dash):
                # available_stamina = max(0.0, stamina_model.stamina() - sp.recover_dec_thr - 300.0)
                # dash_power = min(available_stamina, sp.max_dash_power)
                dash_power = sp.max_dash_power
                dash_accel = unit_vec.set_length_vector(dash_power * ptype.dash_power_rate * sp.effort_init)

                my_vel += dash_accel
                my_pos += my_vel
                my_vel *= ptype.player_decay

                # stamina_model.simulate_dash(ptype, dash_power)
                self_cache.append(Vector2D(my_pos))

    def check_opponent(self, agent: IAgent, ball_trap_pos: Vector2D, dribble_step: int):
        wm = agent.wm
        sp = agent.serverParams
        ball_move_angle:AngleDeg = (ball_trap_pos - Tools.vector2d_message_to_vector2d(wm.ball.position)).th()

        for o in range(12):
            opp = wm.their_players_dict[o]
            if opp is None or opp.uniform_number == 0:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( "###OPP {} is ghost".format(o))
                continue

            if opp.dist_from_self > 20.0:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( "###OPP {} is far".format(o))
                continue

            ptype = agent.get_type(opp.type_id)

            control_area = (sp.catchable_area
                            if opp.is_goalie
                               and ball_trap_pos.x() > sp.their_penalty_area_line_x
                               and ball_trap_pos.abs_y() < sp.penalty_area_half_width
                            else ptype.kickable_area)

            opp_pos = Tools.inertia_point(Tools.vector2d_message_to_vector2d(opp.position), opp.velocity, dribble_step, ptype.player_decay)

            ball_to_opp_rel = (Tools.vector2d_message_to_vector2d(opp.position) - Tools.vector2d_message_to_vector2d(wm.ball.position)).rotated_vector(-ball_move_angle)

            if ball_to_opp_rel.x() < -4.0:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( "###OPP {} is behind".format(o))
                continue

            target_dist = opp_pos.dist(ball_trap_pos)

            if target_dist - control_area < 0.001:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text( "###OPP {} Catch, ball will be in his body".format(o))
                return False

            dash_dist = target_dist
            dash_dist -= control_area * 0.5
            dash_dist -= 0.2
            n_dash = ptype.cycles_to_reach_distance(dash_dist)

            n_turn = 1 if opp.body_count() > 1 else Tools.predict_player_turn_cycle(ptype,
                                                                                      opp.body_direction,
                                                                                      Tools.vector2d_message_to_vector2d(opp.velocity).r(),
                                                                                      target_dist,
                                                                                      (ball_trap_pos - opp_pos).th(),
                                                                                      control_area,
                                                                                      True)

            n_step = n_turn + n_dash if n_turn == 0 else n_turn + n_dash + 1

            bonus_step = 0
            if ball_trap_pos.x() < 30.0:
                bonus_step += 1

            if ball_trap_pos.x() < 0.0:
                bonus_step += 1

            if opp.is_tackling():
                bonus_step = -5

            if ball_to_opp_rel.x() > 0.5:
                bonus_step += smath.bound(0, opp.pos_count(), 8)
            else:
                bonus_step += smath.bound(0, opp.pos_count(), 4)

            if n_step - bonus_step <= dribble_step:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   "###OPP {} catch n_step:{}, dr_step:{}, bonas:{}".format(o, n_step, dribble_step,
                #                                                                        bonus_step))
                return False
            # else:
                # if debug_dribble:
                #     log.sw_log().dribble().add_text(
                #                   "###OPP {} can't catch n_step:{}, dr_step:{}, bonas:{}".format(o, n_step, dribble_step,
                                                                                        #    bonus_step))
        return True
