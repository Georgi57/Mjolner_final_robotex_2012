import time,math,random
import robot_com,videoprocessing
import cv2
import sys,os

class Omnirobot():
    """
    This is the main class that we use get the robot going
    """

    def __init__(self,debug,camera,gate):
        """
        Initialisation of robot devices and videoprocessing module
        """
        self.debug = debug
        self.camera = camera
        self.gate = gate
        
        self.robot=robot_com.robot()
        self.CV=videoprocessing.VideoProcessingOmni(self.camera,self.debug)

        #Main variables
        self.running = True
        self.ball_at_dribbler = False

        #Searching
        self.no_balls_frame_counter = 0
        self.no_gates_frame_counter = 0
        self.last_turn_right = True#ball
        self.gate_right = random.randint(0,1)#gate

        #Drive between gates
        self.gate_state = gate
        
        #Turn to gate
        self.around_the_ball = True
        self.gate_found = 0
        self.start_avoiding_obstacles = 0
        self.driving_between_gates = 0
        self.dribbler_ball_lost = 0

        self.find_ball_after_kick = 0 #Frames more

        #Drive to ball
        self.going_very_fast = 0
        self.ball_found = 0

        #Coilgun
        self.kick_time = 0
        self.coilgun_charging = False
        
        #Screen resolution
        self.screen_x = 320.0
        self.screen_y = 240.0

        #Timeout for going ahead
        self.obstacle_ahead = 0

    def turn_off(self):
        """
        Disables all initialized devices
        """
        self.CV.disable()
        self.robot.stop()
        self.robot.all_off()

    def calculate_distance_and_angle(self,x,y):
        """
        This function calculates ball distance and angle
        according to camera position and height.

        Takes in x and y of the object on hta image.

        Returns distance to the object and angle accoriding to camera direction

        DISTANCES in cm
        """
        
        #Variables, according to which this is calculated
        camera_height = 32.5
        camera_view_angle = 46.8
        camera_blind_angle = 40
        
        #Calculate the distance(question Georgi if you want to understand how)
        ball_distance=camera_height*math.tan(math.radians(camera_blind_angle+camera_view_angle*((self.screen_y-y)/self.screen_y))) - 25

        #And now the angle
        camera_view_angle=53.0
        
        ball_at_angle=0
        if x>=self.screen_x:
            ball_at_angle=camera_view_angle/2*((x-self.screen_x)/self.screen_x)
        else:
            ball_at_angle=camera_view_angle/2*((self.screen_x-x)/self.screen_x)

        #if x!=-1 and self.debug:  
        #    print "Coordinates:",x,y,"Distance to the target:",ball_distance, "At angle ",ball_at_angle
        return ball_distance,ball_at_angle

    def check_robot(self):
        """
        Check robot states
        """
        """
        Check coilgun is charging
        It waits one second after the kick
        """
        if time.time() - self.kick_time > 1 and not self.coilgun_charging:
            self.robot.charge()
            self.coilgun_charging = True
            self.charging_time = time.time()
        
        if self.robot.ball_at_dribbler():
            self.ball_at_dribbler=True
            self.dribbler_ball_lost = 0
        else:
            self.dribbler_ball_lost += 1
            if self.dribbler_ball_lost >= 10:
                self.ball_at_dribbler=False
        """Turn on dribbler if battery is on"""
        #Check if battery is connected
        self.robot.check_battery()
        
        if self.robot.battery:
            self.robot.dribbler_on()
        else:
            self.robot.dribbler_off()

    def get_coordinates(self):
        """
        This function gets coordinates of the ball and gates from videoprocessing module

        Returns target coordinates
        """
        self.CV.grabframe()
        
        if not self.ball_at_dribbler:

            if self.find_ball_after_kick:
                self.CV.justkicked = True
                self.find_ball_after_kick -= 1
            else:
                self.CV.justkicked = False
            
            x,y,x2,y2,over_line = self.CV.findLine_between_object('b')
            if over_line:
                return -1,-1,-1,-1,False
        else:
            x,y,x2,y2,over_line=self.CV.findGoal(self.gate)
        return x,y,x2,y2

    def go_to_gate(self,x,y,x2,y2):
        """Function is called if robot can't find anything for very long time"""
        #print "NO TARGETS FOR TOO LONG"
        
        if self.no_gates_frame_counter>200:
            if self.gate_state == "gbl":
                self.gate_state = "gye"
            else:
                self.gate_state = "gbl"
            self.no_gates_frame_counter = 100

        """First search for a gate"""
        if not self.ball_at_dribbler and self.gate==self.gate_state:
            x,y,x2,y2,state = self.CV.findGoal(self.gate)
        elif self.gate!=self.gate_state:
            x,y,x2,y2,state = self.CV.findGoal(self.gate_state)

        if x==-1:
            self.no_gates_frame_counter+=1

        if x!=-1:
            x=(x+x2)/2
            distance,angle = self.calculate_distance_and_angle(x,y2)

            if self.driving_between_gates > 3:

                speed = 20 + distance/3
                if speed >160:
                    speed = 160

                if distance>100:
                    if x>0.6*self.screen_x:
                        self.robot.go_pid(1,-speed*1.5)
                        self.robot.go_pid(2,speed)
                        self.robot.go_pid(3,0)
                    elif x>0.4*self.screen_x:
                        self.robot.go_pid(1,-speed)
                        self.robot.go_pid(2,speed*1.5)
                        self.robot.go_pid(3,0)
                    else:
                        self.robot.go_forward(speed)
                    return True
                else:
                    self.no_balls_frame_counter = 0
                    self.no_gates_frame_counter = 0
                    if self.gate_state == "gbl":
                        self.gate_state = "gye"
                    else:
                        self.gate_state = "gbl"
                    return False
            else:
                self.driving_between_gates+=1
                self.robot.stop()
                return True
        else:
            return False
            
    def search_for_gate(self):
        """
        If there is no gate in view, this function defines
        which way and at what speed robot should turn

        Makes robot turn around the ball to search for the GATE
        """
        self.no_balls_frame_counter = 0
        frames_until_stop = 2
        frames_until_turn = 5
        self.driving_between_gates = 0
        
        self.no_gates_frame_counter+=1
        
        if self.no_gates_frame_counter>=frames_until_turn:
            
            if self.around_the_ball:
                if not self.gate_right:
                    self.robot.go_pid(1,10)
                    self.robot.go_pid(2,10)
                    self.robot.go_pid(3,32)
                else:
                    self.robot.go_pid(1,-10)
                    self.robot.go_pid(2,-10)
                    self.robot.go_pid(3,-32)
            else:
                turn_speed = 10
                
                if self.gate_right:
                    self.robot.turn_right(turn_speed)
                else:
                    self.robot.turn_left(turn_speed)
                    
        elif self.no_gates_frame_counter>frames_until_stop:
            self.robot.stop()
            black_x,black_y,nx,ny,s = self.CV.findLine_between_object()
            
            if black_x!=-1:
                self.around_the_ball = False
            else:
                self.around_the_ball = True
                if black_x > self.screen_x/2:
                    self.gate_right = False
                else:
                    self.gate_right = True

    def search_for_ball(self):
        """
        If there is no ball in view, this function defines
        which way and at what speed robot should turn

        Makes robot turn to search for the BALL
        """
        frames_until_stop = 3
        frames_until_turn = 5
        self.driving_between_gates = 0
        turn_speed = 15

        if self.ball_found > 0:
            self.ball_found -= 1
        
        self.no_balls_frame_counter+=1
        if self.no_balls_frame_counter>=frames_until_turn:            
            if self.last_turn_right:
                self.robot.turn_right(turn_speed)
            else:
                self.robot.turn_left(turn_speed)
        elif self.no_balls_frame_counter>frames_until_stop:
            self.robot.stop()

    def drive_to_ball(self,distance,angle,x):
        """
        This function defines, how should the robot reach the ball

        Makes robot go towards the ball
        """
        if 0 < self.ball_found <= 5:
            self.ball_found += 1
        if self.ball_found > 5:
            self.no_balls_frame_counter = 0
            self.no_gates_frame_counter = 0

        if distance<5:
            self.going_very_fast = 0
            
            if x>=self.screen_x*0.55:
                self.robot.turn_right(10)
                last_turn_right=True
            elif x<self.screen_x*0.45:
                self.robot.turn_left(10)
                last_turn_right=False
            else:
                self.robot.go_forward(15)
            
        elif distance<20:

            if self.going_very_fast>0:
                self.going_very_fast -= 1
                self.robot.stop()
            else:
                speed = 10 + int(distance/4)
            
                if x>=self.screen_x*0.55:
                    self.robot.go_pid(1,-int(speed + angle))
                    self.robot.go_pid(2,speed)
                    self.robot.go_pid(3,0)
                    last_turn_right=True
                elif x<self.screen_x*0.45:
                    self.robot.go_pid(1,-speed)
                    self.robot.go_pid(2,int(speed + angle))
                    self.robot.go_pid(3,0)
                    last_turn_right=False
                else:
                    self.robot.go_forward(speed)
            
        else:
            speed = 20 + int(distance/3)
            if speed>160:
                speed = 160
            
            if x>=self.screen_x*0.55:
                self.robot.go_pid(1,-int(speed + angle*1.5))
                self.robot.go_pid(2,speed)
                self.robot.go_pid(3,0)
                last_turn_right=True
            elif x<self.screen_x*0.45:
                self.robot.go_pid(1,-speed)
                self.robot.go_pid(2,int(speed + angle*1.5))
                self.robot.go_pid(3,0)
                last_turn_right=False
            else:
                self.robot.go_forward(speed)

            self.going_very_fast = 2
            

    def turn_to_gate(self,x,x2):
        """
        Function that defines, how robot turns to the gate if gate is in view

        Makes robot turn towards gate.
        """
        
        self.no_gates_frame_counter = 0
        self.no_balls_frame_counter = 0
        center_x = int((x+x2)/2)

        #Gate shooting area
        shoot_area_dif = int (0.1 * (x2 - x))

        speed = 20*(abs(center_x-self.screen_x/2)/(self.screen_x/2))
        if speed<7:
            speed = 7
        
        if x2 - shoot_area_dif <= self.screen_x*0.5 - 5:
            self.robot.go_pid(1,-5)
            self.robot.go_pid(2,-5)
            self.robot.go_pid(3,-16)
            self.gate_found = 0
            self.gate_right = False
                
        elif x + shoot_area_dif >= self.screen_x*0.5 - 5:
            self.robot.go_pid(1,5)
            self.robot.go_pid(2,5)
            self.robot.go_pid(3,16)
            self.gate_found = 0
            self.gate_right = True
        else:
            obstacles = self.CV.find_objects_on_the_way_to_object("g")

            long_avoiding_time = False
            if self.start_avoiding_obstacles and time.time() - self.start_avoiding_obstacles > 3:
                long_avoiding_time = True
                            
            if not obstacles or long_avoiding_time:
                """Make certain the gate is in the center"""
                self.robot.stop()
                self.gate_found+=1
                if self.gate_found > 5 and time.time() - self.charging_time > 0.5:
                    """Kick if certain"""
                    self.robot.kick()
                    self.kick_time = time.time()
                    self.coilgun_charging = False
                    self.start_avoiding_obstacles = 0
                    self.gate_found=0
                    self.find_ball_after_kick = 5
            else:
                """Try to avoid obstacles"""
                if not self.start_avoiding_obstacles:
                    self.start_avoiding_obstacles = time.time()
                if obstacles=="left":
                    self.robot.go_left(20)
                else:
                    self.robot.go_right(20)

    def check_for_obstacles(self):
        #Obstacle function here
        timeout = self.CV.find_objects_on_the_way_to_object("t")
        if timeout == "timeout":
            print "Obstacle"
            self.obstacle_ahead+=1
        else:
            self.obstacle_ahead = 0
        if 50 > self.obstacle_ahead > 10:
            self.robot.go_backward(40)
            return True
        elif self.obstacle_ahead >= 50:
            self.robot.stop()
            self.obstacle_ahead = 0
        return False
            
        
    def run(self):
        """
        This function runs the whole algorithm.
        There is an error returning function
        and a gracios turn off in case of error
        """
        t = time.time()
        try:
            while self.running:
                #main function
                self.main()
                #print time.time()-t
                t=time.time()
                if cv2.waitKey(1) == 27:
                    break
        finally:
            #Turn off all devices no matter what happens
            self.turn_off()

    def stop(self):
        """
        Stops the program
        """
        self.running = False

    def main(self):
        """
        This function puts everything together
        """

        #Check all robot states
        self.check_robot()
        
        #Which gate to shoot:
        self.gate = self.robot.which_gate()

        #Get coordinates of the target from videoprocessing module
        x,y,x2,y2=self.get_coordinates()

        #Timeout
        if self.check_for_obstacles():
            return

        if x!=-1:
            """
            In case the target was found 
            """
            #Calculate the distance to it
            ball_distance, ball_at_angle = self.calculate_distance_and_angle(x,y)
            self.driving_between_gates = 0
            
            if self.ball_at_dribbler:
                """
                If robot has got the ball, turn towards the gate and kick
                """
                self.turn_to_gate(x,x2)
            else:
                """
                Otherwise drive to the ball
                """
                self.drive_to_ball(ball_distance,ball_at_angle,x)
        
        else:
            """If searching in one place for too long"""
            if self.no_balls_frame_counter>100 or self.no_gates_frame_counter>100:
                if self.go_to_gate(x,y,x2,y2):
                    return
            """
            If target is not found, search for it
            """
            if self.ball_at_dribbler:
                self.search_for_gate()
            else:
                self.search_for_ball()
            
if __name__ == "__main__":
    r=Omnirobot(True,0,"gye")
    r.run()
