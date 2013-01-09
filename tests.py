import time, robot_com
import cv2.cv as cv
import cv2
import videoprocessing

class Tests():

    running = False
    
    def kick(self):
        robot = robot_com.robot()
        robot.dribbler_on()
        robot.charge()
        print "charge"
        time.sleep(2)
        print "kick"
        robot.kick()

        robot.all_off()

    def show_camera(self,cam_n):
        """Create window"""
        cv2.namedWindow( "Camera", cv.CV_WINDOW_AUTOSIZE )

        """Initialize camera"""
        cam = cv2.VideoCapture(cam_n)
        cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 480)

        while self.running:
            """Get an image from the camera"""
            retval,  frame = cam.read()
            """Show image, function returned any"""
            cv2.line(self.frame,  (160,0), (160,240), (255,0,0), 2)
            if retval:
                cv2.imshow( "Camera", frame )
            print "Press ESC to exit"
            if cv2.waitKey(50) == 27:
                self.running = False
                break

        cv2.destroyAllWindows()
        cam.release()

    def show_small_camera(self,cam_n):
        self.running = True
        """Create window"""
        cv2.namedWindow( "Camera", cv.CV_WINDOW_AUTOSIZE )

        """Initialize camera"""
        cam = cv2.VideoCapture(cam_n)
        cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 320)
        cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

        while self.running:
            """Get an image from the camera"""
            retval,  frame = cam.read()
            """Show image, function returned any"""
            cv2.line(frame,  (160,0), (160,240), (0,0,255), 2)
            if retval:
                cv2.imshow( "Camera", frame )
            print "Press ESC to exit"
            if cv2.waitKey(50) == 27:
                self.running = False
                break

        cv2.destroyAllWindows()
        cam.release()

    def search_for(self,cam_n,target):
        self.running = True

        CV=videoprocessing.VideoProcessingOmni(cam_n,True)

        while self.running:
            CV.grabframe()
            if target == "Ball":
                x,y,x2,y2,over_line=CV.findBalls()
            elif target == "Blue gate":
                x,y,x2,y2,over_line=CV.findGoal("gbl")
            elif target == "Yellow gate":
                x,y,x2,y2,over_line=CV.findGoal("gye")
            print x,y,x2,y2
            print "Press ESC to exit"
            if cv2.waitKey(50) == 27:
                self.running = False
                break

        CV.disable()

    def robot_values(self):
        self.running = True
        robot = robot_com.robot()

        robot.dribbler_on()
        time.sleep(1)
        robot.dribbler_off()

        while self.running:
            time.sleep(0.5)
            
            robot.check_battery()
            print "Battery: ",robot.battery

            
            gate = robot.which_gate()
            print "Gate: ",gate

            ball_at_dribbler = robot.ball_at_dribbler()
            print "Ball at dribbler: ",ball_at_dribbler

        robot.all_off()

    def test_drive(self):
        self.running = True
        robot = robot_com.robot()

        robot.battery = True

        robot.dribbler_on()
        time.sleep(1)

        robot.go_forward(20)
        time.sleep(0.5)

        robot.all_off()
        

    def manual_control(self,cam_n):
        self.running = True
        """
        Turn on robot and camera
        """
        cv2.namedWindow( "Camera", cv.CV_WINDOW_AUTOSIZE )
        cam = cv2.VideoCapture(cam_n)
        cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 320)
        cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
        robot = robot_com.robot()

        #coilgun
        robot.charge()
        kick_time = time.time()

        #variables

        while self.running:
            """Show camera image"""
            retval,  frame = cam.read()
            if retval:
                cv2.imshow( "Camera", frame )
            """Charge coilgun"""
            if time.time() - kick_time > 1:
                robot.charge()
            """Read keyboard interrupts"""
            key = cv2.waitKey(50)
            if key == 107:
                print "kick"
                robot.kick()
                kick_time = time.time()
            elif key == 32:
                print "stop"
                robot.stop()
            elif key == 2490368:
                print "forward"
                robot.go_forward(30)
            elif key == 2621440:
                print "backward"
                robot.go_backward(20)
            elif key == 2424832:
                print "turn left"
                robot.turn_left(15)
            elif key == 2555904:
                print "turn right"
                robot.turn_right(15)
            elif key == 97:
                print "go left"
                robot.go_left(20)
            elif key == 100:
                print "go right"
                robot.go_right(20)
            elif key == 27:
                self.running = False
                break

            
            if key!=-1:
                print key

        robot.all_off()
        cv2.destroyAllWindows()
        cam.release()
        

    def stop(self):
        self.running = False

if __name__ == "__main__":
    r=Tests()
    r.show_small_camera(0)
