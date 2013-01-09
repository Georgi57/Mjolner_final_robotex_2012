import cv2.cv as cv
import cv2
import numpy as np
import time
import threading
import math
from operator import itemgetter

'''EXAMPLES HOW TO USE THIS CODE BELOW'''
global lock # TO USE ONLY WITH SMALL ASUS
lock=threading.RLock() # TO USE ONLY WITH SMALL ASUS
class FrameBufferThread(threading.Thread):
    """
    This is a thread to get rid off camera frame buffer.
    As often as it can, thread gets frames from the camera without processing them.
    """
    running=True
    def run(self):
        global lock, cam
        while self.running:
            time.sleep(0.001)
            lock.acquire()
            try:
                cam.grab()
            finally:
                lock.release()

    def stop(self):
        self.running=False


class BasicsOfVideoprocessing():
    def __init__(self,  camera_num, debug = False, threshold_file_to_read = 'thresholdvalues.txt', buf = False): # 'thresholdvalues_video.txt'

        self.camera_num = camera_num
        self.debug = debug
        self.buf = buf
        self.x, self.y, self.x2, self.y2, self.rectx, self.recty, self.rectx2, self.recty2 = -1, -1, -1, -1, -1, -1, -1, -1
        self.status = False
        self.secondcontourareamax, self.contourareamax = -1, -1
        
        #init functions
        self.init_frametaker()
        self.readinthethresholds(threshold_file_to_read)
        self.init_sections()
        if self.debug:
            self.DEBUG(None,True)
        if self.buf:
            global lock # TO USE ONLY WITH SMALL ASUS
            lock=threading.RLock() # TO USE ONLY WITH SMALL ASUS
            self.bufferstart() # TO USE ONLY WITH SMALL ASUS
        
        #init game variables
        self.ptrobot = float(self.cam_width/2), float(self.cam_height) # robot position - dependent on camera frame size    
        self.ballarea = 5
        self.goalarea = 80
        self.justkicked = False
        
    def findBalls(self): #CHANGED
        self.target = 'b'
        self.setvariables()
        #set variable two ball pos
        self.x, self.y, self.x2, self.y2=-1, -1, -1, -1
        self.status = False #is something disturbing? False =  YES
        self.linedistancex, self.linedistancex = 0, 0
        
        ''' make into sections, section'n' order matters!'''
        section1 = [0, int(self.cam_height*0.4), self.cam_width, self.cam_height] # lower part of pic
        section2 = [0, 0, self.cam_width, int(self.cam_height*0.4)] # upper part of pic # when camera is fixed then sume upper part can be excluded
        sectionlist = [section1,  section2]
        counter = 0
        '''go through the sections till suitable object is found'''
        while self.x==-1 and len(sectionlist) > counter: # first try to get coordinates from lower part of the frame
            roiframe, self.distancex, self.distancey = self.rectmasking(self.frame, sectionlist[counter][0], sectionlist[counter][1], sectionlist[counter][2], sectionlist[counter][3]) #defines  sections we want to watch into
            self.get_ball_position_inner_f(roiframe)
            counter += 1
#        self.y = self.y + sectionlist[counter-1][1] # add them, because starting coordinate (0,0) isn't taken as fixed point, e.g. every frame has a different (0,0) point
        if self.debug:
            self.DEBUG()
        return self.x, self.y, self.x2, self.y2,  self.status

    def findGoal(self, whichcolorgoal): #CHANGED
        ''' parameters: 'gbl' or 'gye' '''
        self.target = whichcolorgoal
        self.setvariables()
        self.rectx, self.recty, self.rectx2, self.recty2 = -1, -1, -1, -1
        self.status = False
        ''' make into sections, section'n' order matters!'''
        section2 = [0, int(self.cam_height*0.4), self.cam_width, self.cam_height] # lower part of pic
        section1 = [0, 0, self.cam_width, int(self.cam_height*0.4)] # upper part of pic # when camera is fixed then sume upper part can be excluded
        sectionlist = [section1,  section2]
        counter = 0
        '''go through the sections till suitable object is found'''
        while len(sectionlist) > counter: # first try to get coordinates from lower part of the frame
            roiframe, self.distancex, self.distancey = self.rectmasking(self.frame, sectionlist[counter][0], sectionlist[counter][1], sectionlist[counter][2], sectionlist[counter][3])
            self.get_goal_position_inner_f(roiframe)
            counter += 1
        if self.debug:
            self.DEBUG()
        return self.rectx, self.recty, self.rectx2, self.recty2,  self.status

    def find_objects_on_the_way_to_object(self, what):  #CHANGED
        #assumes that obj in front of robot (coil can hit ball to the goal) - returns 'left' or 'right' or None
        if what[0] == 'b':
            if self.x == -1: #shouldn't occur ever in game situation - only if this was called before goal was found, but using when Debugging
                sect = [self.cam_width*0.48, 0, self.cam_width*0.52, self.cam_height]  #middle part of pic goal is in front of the robot; OPTIMAL WIDTH? 0.4 and 0.6 should be adjusted - I haven't made any measurements
                print 'hey you don\'t see the goal'
                if self.DEBUG == False:
                    assert 'Balls were checked between the goal when goal wasn\'t found! Search for goal first!'
            else:
                sect = [self.cam_width*0.48, self.y, self.cam_width*0.52, self.cam_height] # 0.1 is for excluding ball from the DRIBBLER. when I know goal position
        
        elif what[0] == 'g':
            if self.rectx == -1: #shouldn't occur ever in game situation - only if this was called before goal was found, but using when Debugging
                sect = [self.cam_width*0.48, 0, self.cam_width*0.52, self.cam_height]  #middle part of pic goal is in front of the robot; OPTIMAL WIDTH? 0.4 and 0.6 should be adjusted - I haven't made any measurements
                print 'hey you don\'t see the goal'
                if self.DEBUG == False:
                    assert 'Balls were checked between the goal when goal wasn\'t found! Search for goal first!'
            else:
                sect = [self.cam_width*0.43, self.recty2, self.cam_width*0.57, self.cam_height] # 0.1 is for excluding ball from the DRIBBLER. when I know goal position
        elif what[0] == 't':
            sect = [0, self.cam_height * 0.95, self.cam_width, self.cam_height]
            
        #make frame
        roiframe2, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0], sect[1], sect[2], sect[3]) # if needed I can optimize to get exact range where balls might disturb kicks

        greenpf = self.color_detection_hsv(roiframe2 ,self.green_threshold_low, self.green_threshold_high)
        orangepf = self.color_detection_hsv(roiframe2 ,self.ball_threshold_low, self.ball_threshold_high)
        whitepf = self.color_detection_bgr(roiframe2 ,self.white_threshold_low, self.white_threshold_high)
        greenpixelcount = cv2.countNonZero(greenpf) 
        orangepixelcount = cv2.countNonZero(orangepf)
        whitepixelcount = cv2.countNonZero(whitepf)
        #print orangepixelcount , (greenpixelcount + whitepixelcount)/(roiframe2.shape[0]*roiframe2.shape[1])*100 # TODO AREAS MUST BE CHECKED!
        if what[0] == 'b':
            if greenpixelcount + whitepixelcount < roiframe2.shape[0]*roiframe2.shape[1]*0.6: #CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                #check where to go... from right
                roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0] + 20, sect[1] - 20, sect[2] +20, sect[3]) 
                greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                greenpixelcountr = cv2.countNonZero(greenpf)
                whitepixelcountr = cv2.countNonZero(whitepf)
                #check where to go... from right
                roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0] - 20, sect[1] - 20, sect[2]-20, sect[3])             
                greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                greenpixelcountl = cv2.countNonZero(greenpf)
                whitepixelcountl = cv2.countNonZero(whitepf)
                
                if self.debug:
                    self.DEBUG()
                if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                    return 'right'
                return 'left' # something is disturbing
        elif what[0] == 'g':
            if self.recty2 > self.ptrobot[1]*0.4:
                if greenpixelcount + whitepixelcount< roiframe2.shape[0]*roiframe2.shape[1]*0.9 or orangepixelcount > 25: #CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                    #check where to go... from right
                    roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0] + 20, sect[1] - 20, sect[2] +20, sect[3]) 
                    greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountr = cv2.countNonZero(greenpf)
                    whitepixelcountr = cv2.countNonZero(whitepf)
                    #check where to go... from right
                    roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0] - 20, sect[1] - 20, sect[2]-20, sect[3])             
                    greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountl = cv2.countNonZero(greenpf)
                    whitepixelcountl = cv2.countNonZero(whitepf)
                    
                    if self.debug:
                        self.DEBUG()
                    if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                        return 'right'
                    return 'left'# something is disturbing
            else:
                if greenpixelcount + whitepixelcount< roiframe2.shape[0]*roiframe2.shape[1]*0.7 or orangepixelcount > 5:#CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                    if self.debug:
                        self.DEBUG()
                    #check where to go... from right
                    roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0] + 20, sect[1] - 20, sect[2] +20, sect[3]) 
                    greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountr = cv2.countNonZero(greenpf)
                    whitepixelcountr = cv2.countNonZero(whitepf)
                    #check where to go... from right
                    roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[0] - 20, sect[1] - 20, sect[2]-20, sect[3])             
                    greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountl = cv2.countNonZero(greenpf)
                    whitepixelcountl = cv2.countNonZero(whitepf)
                    
                    if self.debug:
                        self.DEBUG()
                    if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                        return 'right'
                    return 'left'# something is disturbing
        elif what[0] == 't':
            if greenpixelcount + whitepixelcount< roiframe2.shape[0]*roiframe2.shape[1]*0.7:
                return 'timeout'
            return None
        if self.debug:
            self.DEBUG()
        return None

    def get_line_position_inner_f(self, roiframe, color):
        if color == 'white':
            return self.find_only_line(self.color_detection_bgr(roiframe ,self.white_threshold_low, self.white_threshold_high))
        elif color == 'black':
            return self.find_only_line(self.color_detection_bgr(roiframe ,self.black_threshold_low, self.black_threshold_high))

    def get_goal_position_inner_f(self, roiframe):
        if self.target == 'gye':
            self.find_the_biggest_contour(self.color_detection_hsv(roiframe ,self.yellow_gate_threshold_low, self.yellow_gate_threshold_high), roiframe,  self.goalarea)
        elif self.target == 'gbl':
            self.find_the_biggest_contour(self.color_detection_hsv(roiframe ,self.blue_gate_threshold_low, self.blue_gate_threshold_high), roiframe,  self.goalarea)

    def get_ball_position_inner_f(self, roiframe):
        self.find_the_biggest_contour(self.color_detection_hsv(roiframe ,self.ball_threshold_low, self.ball_threshold_high), roiframe,  self.ballarea)

    def color_detection_hsv(self, frame, thresholdminvalues, thresholdmaxvalues):
        ''' (np.array np.uint8 3channel, list of 3 ints, list of 3 ints) -> np.array np.uint8 1channel'''
        ''' Return thresholded_frame according to thresholdmin/maxvalues'''
        hsv_frame=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV) #convert the image to hsv(Hue, Saturation, Value) so its easier to determine the color to track(hue) 
        #cv2.blur(hsv_frame, (3,  3), hsv_frame)  # TESTing needed does blurring has an effect. 
        colormin = np.asarray(thresholdminvalues, np.uint8)
        colormax = np.asarray(thresholdmaxvalues, np.uint8)# ball color
        thresholded_object_frame = cv2.inRange(hsv_frame, colormin, colormax)
        cv2.dilate(thresholded_object_frame, None)
        if self.debug:
            self.thresholded_object_frame = thresholded_object_frame
            self.DEBUG()
        return thresholded_object_frame

    def color_detection_bgr(self, frame, thresholdminvalues, thresholdmaxvalues):
        cv2.blur(frame, (3,  3), frame)  # TESTing needed does blurring has an effect. 
        colormin = np.asarray(thresholdminvalues, np.uint8)
        colormax = np.asarray(thresholdmaxvalues, np.uint8)# ball color
        thresholded_black_frame = cv2.inRange(frame, colormin, colormax)
        cv2.dilate(thresholded_black_frame, None)
        if self.debug: # otherwise other things arent seen
            self.thresholded_black_frame = thresholded_black_frame
            self.DEBUG()
        return thresholded_black_frame
        
    def find_the_biggest_contour(self, thresholded_roiframe, roiframelocal,  area = 1): # binary array, rgbframe , min areas for object
            ''' (np.array np.uint8 1channel) -> int, np.array'''
            ''' Return the biggest contourarea and contour itself'''
            
            '''image conversion'''
            frame_contours = cv2.dilate(thresholded_roiframe, None) #make white areas more visible
            contours, hierarchy = cv2.findContours(frame_contours, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            ''' find all the contours on the frame and select the biggest'''
            self.contourareamax = 0
            maxcontour = 0
            greenpixels = False
            for i in contours:
                contourarea = cv2.contourArea(i)
                if contourarea > 2 and contourarea > self.contourareamax and contourarea > area: # just to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if  greenpixels == True and retval3[2] > retval3[3]*2:
                        maxcontour = i
                        self.contourareamax = contourarea
                        maxcontourrect =  retval3[0], retval3[1]  + self.distancey, b1, b2+ self.distancey
                    if self.debug:
                        self.DEBUG()
            '''finding the biggest area e.g. find center point when the biggest contour is bigger then area defined'''
            if self.contourareamax:
                # find the center point
                M = cv2.moments(maxcontour)
                self.x,self.y = int(M['m10']/M['m00']), int(M['m01']/M['m00'])
                self.rectx, self.recty, self.rectx2, self.recty2 = maxcontourrect[0], maxcontourrect[1], maxcontourrect[2], maxcontourrect[3] 
                if self.debug:
                    cv2.circle(roiframelocal,(self.x,self.y),5,255,-1)
                    cv2.rectangle(roiframelocal, (maxcontourrect[0], maxcontourrect[1]), (maxcontourrect[2],maxcontourrect[3]), (255, 0, 0)) # the biggest contour is a red rectangle                    
                    self.thresholded_object_frame = thresholded_roiframe
                    self.DEBUG(roiframelocal)
            if self.debug:
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG(roiframelocal)


    def findLine_between_object(self, whichcolorobject = ''): 
        
        if whichcolorobject == '':
            self.setvariables()
            section1 = [int(self.cam_width*0.40), int(self.cam_height*0.6), int(self.cam_width*0.60), int(self.cam_height)*0.9] # how much ahead you would like to see? second point is robots point
            
            #make a roi
            roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, section1[0], section1[1], section1[2], section1[3])
            
            #find black line from roi
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black')
            if blackline_pos[0][0] == - 1:
                return -1, -1, -1, -1, False #'noblack line seen'  # as in you aren't near line
            
            #to bring black line points into same frame of reference
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            
            retval = self.find_intersections((self.ptrobot, (self.ptrobot[0],section1[1])),blackline_pos)
            if self.debug:
                cv2.circle(self.frame, (retval[0], retval[1]),5,(255,0,0),5)
                self.DEBUG()
            if retval[0] == -1:
                return -1, -1, -1, -1, False #'black line and pc line don\'t intersect' #
            return int(retval[0]), int(retval[1]), -1, -1, True # 'black line is x,y -> y number away' # black line and robot line intersection point and True for showing the intersection
        
        elif whichcolorobject[0] == 'b':
            self.findBalls()
            #as there were no objects, then let's not check for lines.
            if self.x == -1: 
                return -1, -1, -1, -1, False
            #BLACK LINE DETECTION
            
            #make a roi frame size not to be too small
            if abs(self.x - self.ptrobot[0]) < 25:
                if self.y > self.cam_height:
                    return self.x, self.y, -1, -1, False
                if self.x > self.ptrobot[0]:
                    helpvariable = self.ptrobot[0] - (25 - abs(self.x - self.ptrobot[0]))
                else:
                    helpvariable = self.ptrobot[0] + (25 - abs(self.x - self.ptrobot[0]))
                    #generate region of interests
                roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, self.x, self.y, helpvariable, self.ptrobot[1]) 
            else:
                roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, self.x, self.y, self.ptrobot[0], self.ptrobot[1]) 
            
            #black line position
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black') # self.roidistancez must be given to give line position one the debug screen on the right place
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            retval = self.find_intersections(((self.x, self.y), self.ptrobot),blackline_pos)
            if self.debug:
                cv2.circle(self.frame, (retval[0], retval[1]),5,(255,0,0),5)
                self.DEBUG()
            if retval == (-1, -1):
                return self.x, self.y, self.x2, self.y2, False #'No line between' # as in you are on the field
            return -1, -1, -1, -1, True #'black line between the ball and robot'
        
        elif whichcolorobject[0] == 'g':
            self.findGoal(whichcolorobject)
            #as there were no objects, then let's not check for lines.
            if self.x == -1: 
                return -1, -1, -1, -1, 'no goal seen'
            #BLACK LINE DETECTION
            
            #make a roi
            roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, self.rectx, self.ptrobot[1] - self.recty, self.rectx2, self.ptrobot[1]) 
            
            #black line position
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black') # self.roidistancez must be given to give line position one the debug screen on the right place
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            retval = self.find_intersections(((self.rectx, self.recty), self.ptrobot),blackline_pos)
            if retval == (-1, -1):
                return self.rectx, self.recty, self.rectx2, self.recty2, 'No line between' # as in you are on the field
            return self.rectx, self.recty, self.rectx2, self.recty2, 'black line between the goal and robot'
        
        
    def findBlackWhiteLine(self):
        # I will give you the answer "are you inside the field or not" and where you need to go to get there.
        self.setvariables()
        
        ''' make into sections'''
        section1 = [int(self.cam_width*0.4), int(self.cam_height*0.4), int(self.cam_width*0.6), int(self.cam_height)] # CONF - how much do we want to see...segment of the pic 

        #create a region of interest
        roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, section1[0], section1[1], section1[2], section1[3])
        #find black line from roi
        blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black')
        if blackline_pos[0][0] == - 1:
            return -1, -1, -1, -1, False #'noblack line seen'  # as in you aren't near line
        
        #find white line
        whiteline_pos = self.get_line_position_inner_f(roiframe.copy(), 'white')
        #to bring points into same frame of reference
        whiteline_pos = (whiteline_pos[0][0] + self.linedistancex, whiteline_pos[0][1] + self.linedistancey), (whiteline_pos[1][0] + self.linedistancex, whiteline_pos[1][1] + self.linedistancey)
        
        #white line and roboline intersection
        retval = self.find_intersections((self.ptrobot, (self.ptrobot[0],section1[1])),whiteline_pos)
        if retval[0] == -1:
            return -1, -1, -1, -1,False # 'white line and pc line don\'t intersect' # as in you are on the field
        #parse intersection point
        retval = int(retval[0]), int(retval[1])
        
        #to bring black line points into same frame of reference
        blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
        
        #black line and roboline intersection
        retval2 = self.find_intersections((self.ptrobot, retval), blackline_pos)
        
        blackwhitelinedistance = retval[1] - retval2[1]
#        print blackwhitelinedistance
        
        if self.debug:
            cv2.circle(self.frame, (retval2[0], retval2[1]),5,(255,0,0),5)
            cv2.circle(self.frame, (retval[0], retval[1]),3,(0,255,0),3)
            cv2.circle(self.frame, (retval[0], retval[1]-int(self.ptrobot[1]*0.20)),1,(0,0,255),1)
            self.DEBUG()
        if retval2 == (-1, -1) or blackwhitelinedistance > self.ptrobot[1]*0.20:
            return int(retval[0]), int(retval[1]), -1, -1,False # as in you are on the field
        return int(retval2[0]), int(retval2[1]), -1, -1,True #'you are outside'
        


    def find_only_line(self, thresholded_frame): 
        # Give in the thresholded_frame and I will give you back to line points if there are any.
        lines = cv2.HoughLines(thresholded_frame, 1, np.pi/30, 20) # TUNING NEEDED! 2 is somekind of distance from coordinate starting point; np.pi/45 is programm is searching lines in every 4th degree ;30 is a threshold
        if lines is not None: # if Nonetype then line not found
            m,n = thresholded_frame.shape
            for rho, theta in lines[0][:1]: # blue for infinite lines (only draw the strongest)
                x0 = np.cos(theta)*rho 
                y0 = np.sin(theta)*rho
                pt1 = ( int(x0 + (m+n)*(-np.sin(theta))), int(y0 + (m+n)*np.cos(theta)))
                pt2 = ( int(x0 - (m+n)*(-np.sin(theta))), int(y0 - (m+n)*np.cos(theta)))
                if self.debug:
                    pt1test = pt1[0] + int(self.linedistancex), pt1[1] + int(self.linedistancey)
                    pt2test = pt2[0] + int(self.linedistancex), pt2[1] + int(self.linedistancey)
                    cv2.line(self.frame,  pt1test, pt2test, (255,255,0), 2)
                    self.thresholded_black_frame = thresholded_frame
                    self.DEBUG()
                return pt1, pt2 # Sees the line
        if self.debug:
            self.thresholded_black_frame = thresholded_frame
            self.DEBUG()
        return (-1,-1),(-1,-1) #doesn't see the line

    

    def find_intersections(self, (line1pt1, line1pt2), (line2pt1, line2pt2)): 
        #tuple, tuple -> intersection x coord, intersection y coord ; if slope is 0 then function will modify the slope a bit
        # to generate artificial slope
        if  line1pt1[0] ==  line1pt2[0]: 
             line1pt1 = line1pt1[0] - 1,  line1pt1[1]
        if  line2pt1[0] ==  line2pt2[0]: 
             line2pt1 = line2pt1[0] - 1,  line2pt1[1]  
        if  line1pt1[1] ==  line1pt2[1]: 
             line1pt1 = line1pt1[0],  line1pt1[1] - 1
        if  line2pt1[1] ==  line2pt2[1]: 
             line2pt1 = line2pt1[0],  line2pt1[1] - 1        
        
        #Make matices
        A = np.matrix(str(float(line1pt1[0])) + ' ' + str(float(line1pt1[1])) + '; ' + str(float(line1pt2[0])) + ' ' + str(float(line1pt2[1])))
        B = np.matrix(str(float(line2pt1[0])) + ' ' + str(float(line2pt1[1])) + '; ' + str(float(line2pt2[0])) + ' ' + str(float(line2pt2[1])))
        
        amin = lambda x1, x2: np.where(x1<x2, x1, x2)
        amax = lambda x1, x2: np.where(x1>x2, x1, x2)
        aall = lambda abools: np.dstack(abools).all(axis=2)
        slope = lambda line: (lambda d: d[:,1]/d[:,0])(np.diff(line, axis=0))

        x11, x21 = np.meshgrid(A[:-1, 0], B[:-1, 0])
        x12, x22 = np.meshgrid(A[1:, 0], B[1:, 0])
        y11, y21 = np.meshgrid(A[:-1, 1], B[:-1, 1])
        y12, y22 = np.meshgrid(A[1:, 1], B[1:, 1])

        m1, m2 = np.meshgrid(slope(A), slope(B))
        m1inv, m2inv = 1/m1, 1/m2

        yi = (m1*(x21-x11-m2inv*y21) + y11)/(1 - m1*m2inv)
        xi = (yi - y21)*m2inv + x21

        xconds = (amin(x11, x12) < xi, xi <= amax(x11, x12), amin(x21, x22) < xi, xi <= amax(x21, x22) )
        yconds = (amin(y11, y12) < yi, yi <= amax(y11, y12), amin(y21, y22) < yi, yi <= amax(y21, y22) )
        if xi[aall(xconds)] and yi[aall(yconds)]:
            return  xi[aall(xconds)], yi[aall(yconds)] # intersection
        return  -1, -1

    def check_for_green_pixels(self, x1, y1, x2, y2, frame, thresholded_frame): 
        # Search green pixels from right areas.
        if self.target[0] == 'b':# or  self.target == 'lineball': #from upper and bottom side
            x1 = x2 - abs(x1 - x2) * 1.3
            x2 = x2 + abs(x1 - x2) * 0.3
            y1 = y2 - abs(y1 - y2) * 1.3
            y2 = y2 + abs(y1 - y2) * 0.3

            area = 15 # how many green pixels are we searching for
        elif self.target[0] == 'g': # only from bottom side
            y2 = y2 + abs(y1 - y2) * 2
            area = 100
        #make roi smaller than the self.frame maximum measures
        if y2 > self.frame.shape[0]:
            y2 = self.frame.shape[0]
        if y1 < 0:
            y1 = 0
        if x1 < 0:
            x1 = 0
        if x2 > self.frame.shape[1]:
            x2 = self.frame.shape[1]
            
        #cut the frame into apropriate size
        roiframe, distancex, distancey = self.rectmasking(self.frame, x1, y1 + self.distancey, x2, y2 + self.distancey)
        
        framebababa = cv2.cvtColor(roiframe,cv2.COLOR_BGR2HSV)
        self.greenfield = cv2.inRange(framebababa, self.green_threshold_low, self.green_threshold_high)
        greenpixels = cv2.countNonZero(self.greenfield)
        if self.debug:
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0))
            self.DEBUG()
        if greenpixels > area: #should be related to y coordinate!!! can't be done, if I don't follow is it upper frame or lower frame
            return True
        return False

    def rectmasking(self, frame, x1, y1, x2 = False, y2 = False): # if second point isn't inserted then it searches position relative to robot position
        ''' np.array(cx, cy, 3), ptx1, pty1, ptx2, pty2 --> array cut frame, float distancex(from previous frame start point), float distancey(from previous frame start point)'''
        if x2 == False:
            x2 = self.ptrobot[0] # use robot x coordinate
        if y2 == False:
           y2 = self.ptrobot[1] # use robots y coordinate
        if abs(x1 - x2) < 6: # pic minimum width
            x1, x2 = x1-3, x2+3
        # assign right first point and second point np.array wants points with specific direction
        if x1 > x2 and y1>y2: # points change place
            x1, x2, y1, y2 = x2, x1, y2, y1
        elif x1 < x2 and y1>y2: # get another rect corner
            x1, x2, y1, y2 = x1, x2, y2, y1
        elif x1>x2 and y1<y2: # get another rect corner
            x1, x2, y1, y2 = x2, x1, y1, y2
        # To make roiframe fit self.frame
        if x1 < 0:
            x1 = 0
        if x2 > self.frame.shape[1]:
            x2 = self.frame.shape[1]
        if y1 < 0:
            y1 = 0
        if y2 > self.frame.shape[0]:
            y2 = self.frame.shape[0]
        # taking out important region
        roiframe = frame.copy()[y1:y2, x1:x2]
        
        return roiframe, x1, y1


    def setvariables(self):
        # set frames to none
        self.thresholded_object_frame = None
        self.greenfield = None
        self.thresholded_black_frame = None

    def grabframe(self):
        
        if self.buf:
            global lock
            ''' to get continuous video from file'''
            lock.acquire()
            try:
                self.cam.grab()
                self.retval, self.frame = self.cam.retrieve()
            finally:
                lock.release()
        else:
            self.retval, self.frame = self.cam.read()
        
        # set frames to none
        self.thresholded_object_frame = None
        self.greenfield = None
        self.thresholded_black_frame = None

    def readinthethresholds(self, filename):
        """
        Import the threshold values that are set by the thresholds.py program
        """
        thresholdvalues=""
        try:
            f = open(filename,  'r')
            thresholdvalues = f.read()
            f.close()
        except:
            print "No threshold values found. Creating blank list"
            for i in range(36):
                thresholdvalues+="0 "

        clrs=thresholdvalues.split()
        for i in range(len(clrs)):
            clrs[i]=int(clrs[i])
        
        #Choose the thresholds (variable names speak for them self)
        self.ball_threshold_low =        np.asarray([clrs[0],clrs[1],clrs[2]], np.uint8)
        self.ball_threshold_high =       np.asarray([clrs[3],clrs[4],clrs[5]], np.uint8)

        self.blue_gate_threshold_low =   np.asarray([clrs[6],clrs[7],clrs[8]], np.uint8)
        self.blue_gate_threshold_high =  np.asarray([clrs[9],clrs[10],clrs[11]], np.uint8)

        self.yellow_gate_threshold_low = np.asarray([clrs[12],clrs[13],clrs[14]], np.uint8)
        self.yellow_gate_threshold_high =np.asarray([clrs[15],clrs[16],clrs[17]], np.uint8)

        self.black_threshold_low =       np.asarray([clrs[18],clrs[19],clrs[20]], np.uint8)
        self.black_threshold_high =      np.asarray([clrs[21],clrs[22],clrs[23]], np.uint8)

        self.white_threshold_low =       np.asarray([clrs[24],clrs[25],clrs[26]], np.uint8)
        self.white_threshold_high =      np.asarray([clrs[27],clrs[28],clrs[29]], np.uint8)

        self.green_threshold_low =       np.asarray([clrs[30],clrs[31],clrs[32]], np.uint8)
        self.green_threshold_high =      np.asarray([clrs[33],clrs[34],clrs[35]], np.uint8)


    def init_frametaker(self):
        self.cam = cv2.VideoCapture(self.camera_num)
        self.cam_width = self.cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 320)
        self.cam_height = self.cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 240)        
        self.cam_width = self.cam.get(cv.CV_CAP_PROP_FRAME_WIDTH)
        self.cam_height = self.cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)
        self.grabframe()
        self.setvariables()
    
    def init_sections(self):
        #ballafterkicksection init
        section1 = [0, int(self.cam_height*0.8), self.cam_width * 0.43, self.cam_height] # lower part of pic left 
        section2 = [self.cam_width * 0.57, int(self.cam_height*0.8), self.cam_width, self.cam_height] # lower part of pic, right
        section3 = [0, int(self.cam_height*0.6), self.cam_width * 0.43,  int(self.cam_height*0.8)] # lower med part of pic, left
        section4 = [self.cam_width * 0.57, int(self.cam_height*0.6), self.cam_width,  int(self.cam_height*0.8)] # lower med part of pic, right
        section5 = [0, int(self.cam_height*0.4), self.cam_width * 0.43, int(self.cam_height*0.6)] # upper med part of pic, left
        section6 = [self.cam_width * 0.57, int(self.cam_height*0.4), self.cam_width, int(self.cam_height*0.6)] # upper med part of pic, right
        section7 = [0, 0, self.cam_width * 0.43, int(self.cam_height*0.4)] # upper part of pic # when camera is fixed then sume upper part can be excluded
        section8 = [self.cam_width * 0.57, 0, self.cam_width, int(self.cam_height*0.4)] # upper part of pic # when camera is fixed then sume upper part can be excluded
        self.ballafterkicksection = [section1,  section2, section3, section4, section5, section6, section7, section8]
        #ball section init        
        sectionlow = [0, int(self.cam_height*0.6), self.cam_width, self.cam_height] # lower part of pic
        sectionup = [0, 0, self.cam_width, int(self.cam_height*0.6)] # upper part of pic # when camera is fixed then sume upper part can be excluded
        self.ballsearchsections = [sectionlow,  sectionup]
    def disable(self):
        """
        Close all windows and release the camera
        """
        if self.buf:
            self.buffer.stop()
        cv2.destroyAllWindows()
        self.cam.release()
    

    def bufferstart(self):
        self.buffer = self.FrameBufferThread()
        self.buffer.daemon = True 
        self.buffer.start() 

    def DEBUG(self, roiframe = None, init = False):
        if init == True:
            cv2.namedWindow( "Camera", cv.CV_WINDOW_AUTOSIZE )
            cv.MoveWindow('Camera', 0, 0)
            cv2.namedWindow( "Thresholded", cv.CV_WINDOW_AUTOSIZE )
            cv.MoveWindow("Thresholded", 450,350)
            cv2.namedWindow( "greenfield", cv.CV_WINDOW_AUTOSIZE )
            cv.MoveWindow("greenfield", 450,0)
            cv2.namedWindow( "roi", cv.CV_WINDOW_AUTOSIZE )
            cv.MoveWindow("roi", 0,350)
            cv2.namedWindow("blacklinethres", cv.CV_WINDOW_AUTOSIZE )
            cv.MoveWindow("blacklinethres", 750, 0)
        else: # what values to write here???
            cv2.imshow('Camera', self.frame)
            if self.thresholded_object_frame == None:
                pass
            else:
                cv2.imshow("Thresholded", self.thresholded_object_frame)
            if self.greenfield == None:
                pass
            else:
                cv2.imshow("greenfield", self.greenfield)
            if roiframe == None:
                cv2.imshow('roi', self.frame)
            else:
                cv2.imshow('roi', roiframe)
            if self.thresholded_black_frame == None:
                pass
            else:
                cv2.imshow('blacklinethres', self.thresholded_black_frame)



    '''TO USE ONLY WITH SMALL ASUS'''
    class FrameBufferThread(threading.Thread):
        """
        This is a thread to get rid off camera frame buffer.
        As often as it can, thread gets frames from the camera without processing them.
        """
        running=True
        def run(self):
            global lock
            while self.running:
                lock.acquire()
                try:
                    self.cam.grab()
                finally:
                    lock.release()

        def stop(self):
            self.running=False


'''In progress advanced functions for more powerful computer...'''

class VideoProcessingOmni(BasicsOfVideoprocessing):
    def find_all_contours(self, thresholded_roiframe, roiframelocal,  area = 1): # binary array, rgbframe , min areas for object
        ''' (np.array np.uint8 1channel) -> int, np.array'''
        ''' Return the biggest contourarea and contour itself'''
        
        '''image conversion'''
        frame_contours = cv2.dilate(thresholded_roiframe, None) #make white areas more visible
        contours, hierarchy = cv2.findContours(frame_contours, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        ''' find all the contours on the frame and select the biggest'''
        #init some variables
        self.listofobjects = []
        self.listofobjectcoordinatesbysize  = []
        for i in contours:
            contourarea = cv2.contourArea(i)
            if self.target[0] == 'b':
                if contourarea > area and contourarea > 2: # area + 2 to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if  greenpixels == True:
                        self.listofobjects.append([contourarea, i])
        '''finding the biggest area e.g. find center point when the biggest contour is bigger then area defined'''
        if self.listofobjects != []:
            # find the center point of the first blob
            sorted(self.listofobjects, key=itemgetter(0)) #sorting list of lists
            for item in self.listofobjects:
                M = cv2.moments(item[1])
                self.listofobjectcoordinatesbysize.append((int(M['m10']/M['m00']) + self.distancex, int(M['m01']/M['m00'])+ self.distancey))
            #print self.listofobjectcoordinatesbysize
            if len(self.listofobjects) > 2:
                (self.x, self.y), (self.x2, self.y2) = self.listofobjectcoordinatesbysize[0], self.listofobjectcoordinatesbysize[1]
            else:
                (self.x, self.y), (self.x2, self.y2) = self.listofobjectcoordinatesbysize[0], (-1, -1)
            if self.debug:
                count = 10
                for item2 in self.listofobjectcoordinatesbysize:
                    cv2.circle(self.frame,(int(item2[0]), int(item2[1])),count,(255,0,0),5)
                    count -= 1
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG()
        elif self.debug:
            self.thresholded_object_frame = thresholded_roiframe
            self.DEBUG()

    def findLine_between_object(self, whichcolorobject = ''):  #what bool output Georgi wants???
        
        if whichcolorobject == '':
            self.setvariables()
            section1 = [int(self.cam_width*0.40), int(self.cam_height*0.6), int(self.cam_width*0.6), int(self.cam_height*0.9)] # how much ahead you would like to see? second point is robots point
            
            #make a roi
            roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, section1[0], section1[1], section1[2], section1[3])
            
            #find black line from roi
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black')
            if blackline_pos[0][0] == - 1:
                return -1, -1, -1, -1, False # as in you aren't near line
            
            #to bring black line points into same frame of reference
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            
            retval = self.find_intersections((self.ptrobot, (self.ptrobot[0],section1[1])),blackline_pos)
            if self.debug:
                cv2.circle(self.frame, (retval[0], retval[1]),5,(255,0,0),5)
                self.DEBUG()
            if retval[0] == -1:
                return -1, -1, -1, -1, False#'black line and pc line don\'t intersect' #
            return int(retval[0]), int(retval[1]), -1, -1, True #'black line is x,y -> y number away' # black line and robot line intersection point and True for showing the intersection
        
        elif whichcolorobject[0] == 'b':
            self.findBalls()
            #as there were no objects, then let's not check for lines.
            if self.x == -1: 
                return -1, -1, -1, -1, False
            #BLACK LINE DETECTION
            
            #make a roi frame size not to be too small
            for ball in self.listofobjectcoordinatesbysize:
                if ball[1] > self.cam_height*0.84:
                    return ball[0], ball[1], -1, -1, False
                if abs(ball[0] - self.ptrobot[0]) < 25:
                    if ball[0] > self.ptrobot[0]:
                        helpvariable = self.ptrobot[0] - (25 - abs(ball[0]- self.ptrobot[0]))
                    else:
                        helpvariable = self.ptrobot[0] + (25 - abs(ball[0] - self.ptrobot[0]))
                        #generate region of interests
                    #print ball[0], ball[1], helpvariable, self.cam_height* 0.85
                    roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, ball[0], ball[1], helpvariable, self.cam_height* 0.85) 
                else:
                    #print ball[0], ball[1], self.ptrobot[0], self.cam_height * 0.85
                    roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, ball[0], ball[1], self.ptrobot[0], self.cam_height * 0.85) 
                
                #black line position
                blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black') # self.roidistancez must be given to give line position one the debug screen on the right place
                blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
                retval = self.find_intersections(((ball[0], ball[1]), self.ptrobot),blackline_pos)
                if self.debug:
                    cv2.circle(self.frame, (retval[0], retval[1]),5,(255,0,0),5)
                    self.DEBUG()
                if retval == (-1, -1):
                    return ball[0], ball[1], -1, -1, False #'No line between' # as in you are on the field
            return -1, -1, -1, -1, False #'black line between the ball and robot or BALL NOT SEEN'
        
        elif whichcolorobject[0] == 'g':
            self.findGoal(whichcolorobject)
            #as there were no objects, then let's not check for lines.
            if self.x == -1: 
                return -1, -1, -1, -1, False
            #BLACK LINE DETECTION
            
            #make a roi
            roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, self.rectx, self.ptrobot[1] - self.recty, self.rectx2, self.ptrobot[1]) 
            
            #black line position
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black') # self.roidistancez must be given to give line position one the debug screen on the right place
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            retval = self.find_intersections(((self.rectx, self.recty), self.ptrobot),blackline_pos)
            if retval == (-1, -1):
                return self.rectx, self.recty, self.rectx2, self.recty2, False#'No line between' # as in you are on the field
            return self.rectx, self.recty, self.rectx2, self.recty2, True#'black line between the goal and robot'
        
        


    def get_ball_position_inner_f(self, roiframe):
        self.find_all_contours(self.color_detection_hsv(roiframe ,self.ball_threshold_low, self.ball_threshold_high), roiframe,  self.ballarea)
    def findBalls(self): #CHANGED
        self.target = 'b'
        self.setvariables()
        #set variable two ball pos
        self.x, self.y, self.x2, self.y2=-1, -1, -1, -1
        self.status = False #is something disturbing? False =  YES
        self.linedistancex, self.linedistancex = 0, 0
        
        ''' make into sections, section'n' order matters!'''
        # after kick
        if self.justkicked:
            sectionlist = self.ballafterkicksection
        else:
            sectionlist = self.ballsearchsections
        counter = 0
        '''go through the sections till suitable object is found'''
        while self.x==-1 and len(sectionlist) > counter: # first try to get coordinates from lower part of the frame
            roiframe, self.distancex, self.distancey = self.rectmasking(self.frame, sectionlist[counter][0], sectionlist[counter][1], sectionlist[counter][2], sectionlist[counter][3]) #defines  sections we want to watch into
            self.get_ball_position_inner_f(roiframe)
            counter += 1
#        self.y = self.y + sectionlist[counter-1][1] # add them, because starting coordinate (0,0) isn't taken as fixed point, e.g. every frame has a different (0,0) point
        if self.debug:
            self.DEBUG()
        return self.x, self.y, self.x2, self.y2,  self.status

    def find_objects_on_the_way_to_object(self, what):  #CHANGED
        #assumes that obj in front of robot (coil can hit ball to the goal) - returns 'left' or 'right' or None
        if what[0] == 'b':
            if self.x == -1: #shouldn't occur ever in game situation - only if this was called before goal was found, but using when Debugging
                section = [self.cam_width*0.48, 0, self.cam_width*0.52, self.cam_height]  #middle part of pic goal is in front of the robot; OPTIMAL WIDTH? 0.4 and 0.6 should be adjusted - I haven't made any measurements
                print 'hey you don\'t see the goal'
                sect = [section]
                if self.DEBUG == False:
                    assert 'Balls were checked between the goal when goal wasn\'t found! Search for goal first!'
            else:
                section = [self.cam_width*0.48, self.y, self.cam_width*0.52, self.cam_height] # 0.1 is for excluding ball from the DRIBBLER. when I know goal position
                sect = [section]
        
        elif what[0] == 'g':
            if self.rectx == -1: #shouldn't occur ever in game situation - only if this was called before goal was found, but using when Debugging
                section = [self.cam_width*0.48, 0, self.cam_width*0.52, self.cam_height]  #middle part of pic goal is in front of the robot; OPTIMAL WIDTH? 0.4 and 0.6 should be adjusted - I haven't made any measurements
                print 'hey you don\'t see the goal'
                sect = [section]
                if self.DEBUG == False:
                    assert 'Balls were checked between the goal when goal wasn\'t found! Search for goal first!'
            else:
                if self.recty2 < self.ptrobot[1]*0.1:
                    section1 = [self.cam_width*0.43, self.cam_height*0.8, self.cam_width*0.57, self.cam_height] #
                    section2 = [self.cam_width*0.45, self.cam_height*0.6, self.cam_width*0.55, self.cam_height*0.8] # 
                    section3 = [self.cam_width*0.48, self.cam_height*0.1, self.cam_width*0.52, self.cam_height*0.6] # 0.1 is for excluding ball from the DRIBBLER. when I know goal position 
                    sect = [section1, section2, section3]
                    if self.debug:
                        cv2.rectangle(self.frame, (int(self.cam_width*0.43), int(self.cam_height*0.8)), (int(self.cam_width*0.57), int(self.cam_height)),  (255, 255, 0))
                        cv2.rectangle(self.frame, (int(self.cam_width*0.45), int(self.cam_height*0.6)), (int( self.cam_width*0.55), int(self.cam_height*0.8)),  (255, 255, 0))
                        cv2.rectangle(self.frame, (int(self.cam_width*0.48), int( self.cam_height*0.1)), (int(self.cam_width*0.52), int(self.cam_height*0.6)),  (255, 255, 0))
                        self.DEBUG()
                elif self.recty2 < self.ptrobot[1]*0.5:
                    section1 = [self.cam_width*0.43, self.cam_height*0.8, self.cam_width*0.57, self.cam_height] #
                    section2 = [self.cam_width*0.45, self.cam_height*0.5, self.cam_width*0.55, self.cam_height*0.8]           
                    sect = [section1, section2]
                    if self.debug:
                        cv2.rectangle(self.frame, (int(self.cam_width*0.43), int(self.cam_height*0.8)), (int(self.cam_width*0.57), int(self.cam_height)),  (255, 255, 0))
                        cv2.rectangle(self.frame, (int(self.cam_width*0.45), int(self.cam_height*0.5)), (int( self.cam_width*0.55), int(self.cam_height*0.8)),  (255, 255, 0))
                        self.DEBUG()
                else:
                    if self.recty2 + 30 > self.cam_height:
                        section = [self.cam_width*0.43, self.cam_height - 1, self.cam_width*0.57, self.cam_height] # 0.1 is for excluding ball from the DRIBBLER. when I know goal position 
                    else:
                        section = [self.cam_width*0.43, self.recty2 + 30, self.cam_width*0.57, self.cam_height] # 0.1 is for excluding ball from the DRIBBLER. when I know goal position 
                    sect = [section]
                    if self.debug:
                        cv2.rectangle(self.frame, (int(self.cam_width*0.43), int(self.recty2 + 30)), (int(self.cam_width*0.57), int(self.cam_height)),  (255, 255, 0))
                        self.DEBUG()
        elif what[0] == 't':
            section = [0, self.cam_height * 0.95, self.cam_width, self.cam_height]
            sect = [section]
        count = 0
        while len(sect) > count:
            #make frame
            roiframe2, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0], sect[count][1], sect[count][2], sect[count][3]) # if needed I can optimize to get exact range where balls might disturb kicks
            greenpf = self.color_detection_hsv(roiframe2 ,self.green_threshold_low, self.green_threshold_high)
            orangepf = self.color_detection_hsv(roiframe2 ,self.ball_threshold_low, self.ball_threshold_high)
            whitepf = self.color_detection_bgr(roiframe2 ,self.white_threshold_low, self.white_threshold_high)
            greenpixelcount = cv2.countNonZero(greenpf) 
            orangepixelcount = cv2.countNonZero(orangepf)
            whitepixelcount = cv2.countNonZero(whitepf)
            if what[0] == 'g':
                if ((greenpixelcount + whitepixelcount) < roiframe2.shape[0]*roiframe2.shape[1]*0.8 or orangepixelcount > 150) and count == 0: #CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                    #check where to go... from right
                    roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] + 20, sect[count][1], sect[count][2] +20, sect[count][3]) 
                    greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountr = cv2.countNonZero(greenpf)
                    whitepixelcountr = cv2.countNonZero(whitepf)
                    #check where to go... from right
                    roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] - 20, sect[count][1], sect[count][2]-20, sect[count][3])             
                    greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountl = cv2.countNonZero(greenpf)
                    whitepixelcountl = cv2.countNonZero(whitepf)
                    if self.debug:
                        self.DEBUG()
                    if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                        return 'right'
                    return 'left'# something is disturbing
                elif (greenpixelcount + whitepixelcount< roiframe2.shape[0]*roiframe2.shape[1]*0.8 or orangepixelcount > 50) and count == 1: #CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                    #check where to go... from right
                    roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] + 20, sect[count][1], sect[count][2] +20, sect[count][3]) 
                    greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountr = cv2.countNonZero(greenpf)
                    whitepixelcountr = cv2.countNonZero(whitepf)
                    #check where to go... from right
                    roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] - 20, sect[count][1], sect[count][2]-20, sect[count][3])             
                    greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountl = cv2.countNonZero(greenpf)
                    whitepixelcountl = cv2.countNonZero(whitepf)
                    if self.debug:
                        self.DEBUG()
                    if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                        return 'right'
                    return 'left'# something is disturbing
                elif ((greenpixelcount + whitepixelcount)< roiframe2.shape[0]*roiframe2.shape[1]*0.9 or orangepixelcount > 25) and count == 2:#CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                    #check where to go... from right
                    roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] + 20, sect[count][1] - 20, sect[count][2] +20, sect[count][3]) 
                    greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountr = cv2.countNonZero(greenpf)
                    whitepixelcountr = cv2.countNonZero(whitepf)
                    #check where to go... from right
                    roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] - 20, sect[count][1] - 20, sect[count][2]-20, sect[count][3])             
                    greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                    whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                    greenpixelcountl = cv2.countNonZero(greenpf)
                    whitepixelcountl = cv2.countNonZero(whitepf)
                    if self.debug:
                        self.DEBUG()
                    if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                        return 'right'
                    return 'left'# something is disturbing
            count += 1
            
            
        if what[0] == 'b':
            if greenpixelcount + whitepixelcount < roiframe2.shape[0]*roiframe2.shape[1]*0.6: #CONF NEEDED WHAT PERCENTAGE IS USUALLY SEEN? "0.6"
                #check where to go... from right
                roiframe2right, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] + 20, sect[count][1] - 20, sect[count][2] +20, sect[count][3]) 
                greenpf = self.color_detection_hsv(roiframe2right ,self.green_threshold_low, self.green_threshold_high)
                whitepf = self.color_detection_bgr(roiframe2right ,self.white_threshold_low, self.white_threshold_high)
                greenpixelcountr = cv2.countNonZero(greenpf)
                whitepixelcountr = cv2.countNonZero(whitepf)
                #check where to go... from right
                roiframe2left, self.distancex, self.distancey = self.rectmasking(self.frame, sect[count][0] - 20, sect[count][1] - 20, sect[count][2]-20, sect[count][3])             
                greenpf = self.color_detection_hsv(roiframe2left,self.green_threshold_low, self.green_threshold_high)
                whitepf = self.color_detection_bgr(roiframe2left,self.white_threshold_low, self.white_threshold_high)
                greenpixelcountl = cv2.countNonZero(greenpf)
                whitepixelcountl = cv2.countNonZero(whitepf)
                
                if self.debug:
                    self.DEBUG()
                if whitepixelcountr + greenpixelcountr > whitepixelcountl + greenpixelcountl:
                    return 'right'
                return 'left' # something is disturbing
        
        elif what[0] == 't':
            if greenpixelcount + whitepixelcount < roiframe2.shape[0]*roiframe2.shape[1]*0.7:
                return 'timeout'
            return None
        if self.debug:
            self.DEBUG()
        return None


class VideoProcessingDiff(BasicsOfVideoprocessing):
    def __init__(self,  camera_num, debug = False, threshold_file_to_read = 'thresholdvalues.txt'): # 'thresholdvalues_video.txt'
        self.camera_num = camera_num
        self.debug = debug
        self.x, self.y, self.x2, self.y2, self.rectx, self.recty, self.rectx2, self.recty2 = -1, -1, -1, -1, -1, -1, -1, -1
        self.status = False
        self.secondcontourareamax, self.contourareamax = -1, -1
        
        #init functions
        self.init_frametaker()
        self.readinthethresholds(threshold_file_to_read)
        if self.debug:
            self.DEBUG(None,True)
        self.bufferstart() # TO USE ONLY WITH SMALL ASUS
        
        self.grabframe()
        #init game variables
        self.ptrobot = float(self.cam_width/2), float(self.cam_height) # robot position - dependent on camera frame size    
        self.ballarea = 5
        self.goalarea = 100
        
    def grabframe(self):
        global lock, cam
        ''' to get continuous video from file'''
        lock.acquire()
        try:
            cam.grab()
            self.retval, self.frame = cam.retrieve()
        finally:
            lock.release()
        
        # set frames to none
        self.thresholded_object_frame = None
        self.greenfield = None
        self.thresholded_black_frame = None
    
    def disable(self):
        """
        Close all windows and release the camera
        """    
        global cam
        self.buffer.stop()
        cv2.destroyAllWindows()
        cam.release()
    def bufferstart(self):
        self.buffer = FrameBufferThread()
        self.buffer.daemon = True 
        self.buffer.start() 

    def init_frametaker(self):
        global cam
        cam = cv2.VideoCapture(self.camera_num)
        self.cam_width = cam.set(cv.CV_CAP_PROP_FRAME_WIDTH, 320)
        self.cam_height = cam.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 240)        
        self.cam_width = cam.get(cv.CV_CAP_PROP_FRAME_WIDTH)
        self.cam_height = cam.get(cv.CV_CAP_PROP_FRAME_HEIGHT)
        self.setvariables()
    def find_the_biggest_contour(self, thresholded_roiframe, roiframelocal,  area = 1): # binary array, rgbframe , min areas for object
        ''' (np.array np.uint8 1channel) -> int, np.array'''
        ''' Return the biggest contourarea and contour itself'''
        
        '''image conversion'''
        frame_contours = cv2.dilate(thresholded_roiframe, None) #make white areas more visible
        contours, hierarchy = cv2.findContours(frame_contours, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        ''' find all the contours on the frame and select the biggest'''
        #init some variables
        self.contourareamax = 0
        maxcontour = 0
        contourarea = 0
        maxcontourrect = -1,0,0,0
        greenpixels = False
        secondmaxcontour = 0
        secondmaxcontourrect = -1,0,0,0
        self.secondcontourareamax = 0
        for i in contours:
            contourarea = cv2.contourArea(i)
            if self.target[0] == 'b':
                if contourarea > 2 and contourarea > self.secondcontourareamax and contourarea > area: # just to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if  greenpixels == True:
                        if  contourarea > self.contourareamax:
                            secondmaxcontour = maxcontour
                            secondmaxcontourrect = maxcontourrect
                            self.secondcontourareamax = self.contourareamax
                            maxcontour = i
                            maxcontourrect =  retval3[0], retval3[1], b1, b2
                            self.contourareamax = contourarea
                        else:
                            secondmaxcontour = i
                            secondmaxcontourrect = retval3[0], retval3[1], b1, b2
                            self.secondcontourareamax = contourarea
            else:
                 if contourarea > 2 and contourarea > self.contourareamax and contourarea > area: # just to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if greenpixels == True:
                        maxcontour = i
                        self.contourareamax = contourarea
                        maxcontourrect =  retval3[0], retval3[1], b1, b2
        '''finding the biggest area e.g. find center point when the biggest contour is bigger then area defined'''
        if maxcontourrect[0] != -1 and self.target[0] == 'b':
            # find the center point of the first blob
            M = cv2.moments(maxcontour)
            self.x,self.y = int(M['m10']/M['m00']) + self.distancex, int(M['m01']/M['m00']) + self.distancey
            
            # second ball only if it exists
            if secondmaxcontourrect[0] != -1:
                #find second blobs center
                N = cv2.moments(secondmaxcontour)
                self.x2,self.y2 = int(N['m10']/N['m00']) + self.distancex, int(N['m01']/N['m00']) + self.distancey
            if self.debug:
                cv2.circle(self.frame,(self.x,self.y),5,(255,0,0),5)
                cv2.rectangle(self.frame, (maxcontourrect[0] + self.distancex, maxcontourrect[1] + self.distancey), (maxcontourrect[2] + self.distancex,maxcontourrect[3]+ self.distancey), (255, 0, 0)) # the biggest contour is a red rectangle                    
                if secondmaxcontourrect[0] != -1:
                    cv2.circle(self.frame,(self.x2+ self.distancex,self.y2+ self.distancey),2,(255,0,0),2)
                    cv2.rectangle(self.frame, (secondmaxcontourrect[0] + self.distancex, secondmaxcontourrect[1] + self.distancey), (secondmaxcontourrect[2]+ self.distancex,secondmaxcontourrect[3]+ self.distancey), (255,0, 0)) # the biggest contour is a red rectangle                    
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG(roiframelocal)
        
        elif maxcontourrect[0] != -1:
            self.rectx, self.recty, self.rectx2, self.recty2 = maxcontourrect[0], self.distancemaxcontourrect[1], maxcontourrect[2],maxcontourrect[3]
            '''finding the biggest area e.g. find center point when the biggest contour is bigger then area defined'''
            if self.debug:
                cv2.rectangle(roiframelocal, (maxcontourrect[0] + self.distancex, maxcontourrect[1] + self.distancey), (maxcontourrect[2] + self.distancex,maxcontourrect[3]+ self.distancey), (255, 0, 0)) # the biggest contour is a red rectangle                    
                if secondmaxcontourrect[0] != -1:
                    cv2.circle(self.frame,(self.x2,self.y2),5,(255,0,0),5)
                    cv2.rectangle(self.frame, (secondmaxcontourrect[0], secondmaxcontourrect[1]), (secondmaxcontourrect[2],secondmaxcontourrect[3]), (255,0, 0)) # the biggest contour is a red rectangle                    
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG()
            self.rectx, self.recty, self.rectx2, self.recty2 = maxcontourrect
            if self.debug:
                cv2.rectangle(self.frame, (maxcontourrect[0], maxcontourrect[1]), (maxcontourrect[2],maxcontourrect[3]), (255, 0, 0)) # the biggest contour is a red rectangle                    
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG(self.frame)
        if self.debug:
            self.thresholded_object_frame = thresholded_roiframe
            self.DEBUG(roiframelocal)



    def find_all_contours(self, thresholded_roiframe, roiframelocal,  area = 1): # binary array, rgbframe , min areas for object
        ''' (np.array np.uint8 1channel) -> int, np.array'''
        ''' Return the biggest contourarea and contour itself'''
        
        '''image conversion'''
        frame_contours = cv2.dilate(thresholded_roiframe, None) #make white areas more visible
        contours, hierarchy = cv2.findContours(frame_contours, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        ''' find all the contours on the frame and select the biggest'''
        #init some variables
        self.listofobjects = []
        self.listofobjectcoordinatesbysize  = []
        for i in contours:
            contourarea = cv2.contourArea(i)
            if self.target[0] == 'b':
                if contourarea > area and contourarea > 2: # area + 2 to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if  greenpixels == True:
                        self.listofobjects.append([contourarea, i])
        '''finding the biggest area e.g. find center point when the biggest contour is bigger then area defined'''
        if self.listofobjects != []:
            # find the center point of the first blob
            sorted(self.listofobjects, key=itemgetter(0)) #sorting list of lists
            for item in self.listofobjects:
                M = cv2.moments(item[1])
                self.listofobjectcoordinatesbysize.append((int(M['m10']/M['m00']) + self.distancex, int(M['m01']/M['m00'])+ self.distancey))
            if len(self.listofobjects) > 2:
                (self.x, self.y), (self.x2, self.y2) = self.listofobjectcoordinatesbysize[0], self.listofobjectcoordinatesbysize[1]
            else:
                (self.x, self.y), (self.x2, self.y2) = self.listofobjectcoordinatesbysize[0], (-1, -1)
            if self.debug:
                count = 10
                for item2 in self.listofobjectcoordinatesbysize:
                    cv2.circle(self.frame,item2,count,(255,0,0),5)
                    count -= 1
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG()
        elif self.debug:
            self.thresholded_object_frame = thresholded_roiframe
            self.DEBUG()

    def findLine_between_object(self, whichcolorobject = ''):  #what bool output Georgi wants???
        
        if whichcolorobject == '':
            self.setvariables()
            section1 = [int(self.cam_width*0.40), int(self.cam_height*0.6), int(self.cam_width*0.6), int(self.cam_height*0.9)] # how much ahead you would like to see? second point is robots point
            
            #make a roi
            roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, section1[0], section1[1], section1[2], section1[3])
            
            #find black line from roi
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black')
            if blackline_pos[0][0] == - 1:
                return -1, -1, 'noblack line seen'  # as in you aren't near line
            
            #to bring black line points into same frame of reference
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            
            retval = self.find_intersections((self.ptrobot, (self.ptrobot[0],section1[1])),blackline_pos)
            if self.debug:
                cv2.circle(self.frame, (retval[0], retval[1]),5,(255,0,0),5)
                self.DEBUG()
            if retval[0] == -1:
                return -1, -1, 'black line and pc line don\'t intersect' #
            return int(retval[0]), int(retval[1]),'black line is x,y -> y number away' # black line and robot line intersection point and True for showing the intersection
        
        elif whichcolorobject[0] == 'b':
            self.findBalls()
            #as there were no objects, then let's not check for lines.
            if self.x == -1: 
                return -1, -1, -1, -1, False
            #BLACK LINE DETECTION
            
            #make a roi frame size not to be too small
            for ball in self.listofobjectcoordinatesbysize:
                if ball[1] > self.cam_height*0.84:
                    return ball[0], ball[1], -1, -1, False
                if abs(ball[0] - self.ptrobot[0]) < 25:
                    if ball[0] > self.ptrobot[0]:
                        helpvariable = self.ptrobot[0] - (25 - abs(ball[0]- self.ptrobot[0]))
                    else:
                        helpvariable = self.ptrobot[0] + (25 - abs(ball[0] - self.ptrobot[0]))
                        #generate region of interests
                    #print ball[0], ball[1], helpvariable, self.cam_height* 0.85
                    roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, ball[0], ball[1], helpvariable, self.cam_height* 0.85) 
                else:
                    #print ball[0], ball[1], self.ptrobot[0], self.cam_height * 0.85
                    roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, ball[0], ball[1], self.ptrobot[0], self.cam_height * 0.85) 
                
                #black line position
                blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black') # self.roidistancez must be given to give line position one the debug screen on the right place
                blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
                retval = self.find_intersections(((ball[0], ball[1]), self.ptrobot),blackline_pos)
                if self.debug:
                    cv2.circle(self.frame, (retval[0], retval[1]),5,(255,0,0),5)
                    self.DEBUG()
                if retval == (-1, -1):
                    return ball[0], ball[1], -1, -1, False #'No line between' # as in you are on the field
            return -1, -1, -1, -1, False #'black line between the ball and robot or BALL NOT SEEN'
        
        elif whichcolorobject[0] == 'g':
            self.findGoal(whichcolorobject)
            #as there were no objects, then let's not check for lines.
            if self.x == -1: 
                return -1, -1, -1, -1, 'no goal seen'
            #BLACK LINE DETECTION
            
            #make a roi
            roiframe, self.linedistancex, self.linedistancey = self.rectmasking(self.frame, self.rectx, self.ptrobot[1] - self.recty, self.rectx2, self.ptrobot[1]) 
            
            #black line position
            blackline_pos = self.get_line_position_inner_f(roiframe.copy(), 'black') # self.roidistancez must be given to give line position one the debug screen on the right place
            blackline_pos = (blackline_pos[0][0] + self.linedistancex, blackline_pos[0][1] + self.linedistancey), (blackline_pos[1][0] + self.linedistancex, blackline_pos[1][1] + self.linedistancey)
            retval = self.find_intersections(((self.rectx, self.recty), self.ptrobot),blackline_pos)
            if retval == (-1, -1):
                return self.rectx, self.recty, self.rectx2, self.recty2, 'No line between' # as in you are on the field
            return self.rectx, self.recty, self.rectx2, self.recty2, 'black line between the goal and robot'
        
        


    def get_ball_position_inner_f(self, roiframe):
        self.target = 'b'
        self.find_all_contours(self.color_detection_hsv(roiframe ,self.ball_threshold_low, self.ball_threshold_high), roiframe,  self.ballarea)






if __name__ == '__main__': # condition doesn't run when fail is imported by another fail... when this fail is run then it initiates.
#cheat sheet:  camera_num, debug = False, threshold_file_to_read = 'thresholdvalues.txt', buf = False): # 'thresholdvalues_video.txt'
#    CV = VideoProcessingOmni(0,True,  'thresholdvalues_video.txt')
#    CV = VideoProcessingOmni('find_objects_on_the_way_to_goal.webm',True,  'thresholdvalues_video.txt')
#    CV = VideoProcessingOmni(1,True,  'thresholdvalues.txt')
#    CV = VideoProcessingOmni('ballonthelinewiththebluegoal.webm',True,  'thresholdvalues_video.txt')
    CV = VideoProcessingOmni(1,True,  'thresholdvalues.txt')
#    CV = BasicsOfVideoprocessing('ball_behind_line.webm',True,  'thresholdvalues_video.txt')
#    CV = BasicsOfVideoprocessing('find_objects_on_the_way_to_goal.webm',True,  'thresholdvalues_video.txt')
#    CV = BasicsOfVideoprocessing('ball_behind_line.webm',True,  'thresholdvalues_video.txt')

#    CV = BasicsOfVideoprocessing('ball_behind_line.webm',True, 'thresholdvalues_t4.txt')
#    CV = BasicsOfVideoprocessing('yellow_gate.webm',True, 'thresholdvalues_t4.txt')
#    CV = BasicsOfVideoprocessing('blue_gate.webm',True, 'thresholdvalues_video.txt')
#    CV = VideoProcessingOmni('howfarlneisseen.webm',True, 'thresholdvalues_video.txt')
#    CV = BasicsOfVideoprocessing(0,True)
#    CV.justkicked = True
    while 1:
        CV.grabframe()
#        measuretime = time.time()
#        print CV.secondcontourareamax
#        print CV.contourareamax
#        print CV.findBalls()
#        print 
        CV.findGoal('gbl')
#        print CV.findLine_between_object('b')
#        print CV.findLine_between_object('bye')
#        print CV.findLine_between_object('gbl')

#        CV.findBalls()
#        print CV.findLine_between_object('b')
#        print CV.findBlackWhiteLine()
#        print CV.findLine_between_object()
#        CV.findGoal('gye')
        print CV.find_objects_on_the_way_to_object('gbl')
#        print time.time() - measuretime
        if cv2.waitKey(1) == 27:
            break
    CV.disable()

'''
Examples:


Initiating BasicsOfVideoprocessing class (or selectively VideoProcessingOmni class #atm only difference is that with this you can find two ball coordinates)
... = BasicsOfVideoprocessing(camera_num, debug = False, threshold_file_to_read = 'thresholdvalues.txt', buf = False)
ex: 
>> CV = BasicsOfVideoprocessing(1) #competition mode for omni - pic from first camera
>> CV = BasicsOfVideoprocessing('video.avi', True, 'thresholdvalues_video.txt') #video stream from file with debug windows and threshold values from file 'thresholdvalues_video.txt' file

Get ball coordinates: 
ball1 x coordinate, ball1 y coordinate, ball2 x coordinate, ball2 y coordinate, bool (Is something disturbing) = CV.findBalls()
ex:
>> retval = CV.findBalls()
PS. to get ball sizes ask.. 
>>    self.secondcontourareamax
>>    self.contourareamax

Get goal pos:
goal upper left corner x coordinate, goal upper left corner y coordinate, goal lower right corner x coordinate, goal lower right corner y coordinate, bool (Is something disturbing?) = CV.findGoal(goal and color)
ex:
>> retval = CV.findGoal('gye') # yellow goal
>> retval = CV.findGoal('gbl') # blue goal

Is black line between object or in front and robot?
point1 x coordinate, point1 y coordinate, point2 x coordinate,  point2 y coordinate, bool (Is something disturbing) = findLine_between_object(whichcolorobject = None)
optional parameters 'gye' , 'gbl' , 'b'
>> retval =  findLine_between_object('gbl') # searches back line between blue goal and robot
>> retval =  findLine_between_object('b') # searches back line between ball and robot
>> retval =  findLine_between_object() # searches back line infront of robot

For finding objects between robot and goal. Assumption is that goal is seen and is targeted. Designed for making a final before the kick check for any disturbing objects. For optimization, the function doesn't search the goal in reality, just for balls between robot and goal from the previous frame.
CV.findGoal('gbl') #to find a goal first.. if goal position is true, then use next function
bool = CV.find_objects_on_the_way_to_goal() #(something disturbing = True, False = you can shoot)
>>bool = CV.find_objects_on_the_way_to_goal()


    def find_the_biggest_contour(self, thresholded_roiframe, roiframelocal,  area = 1): # binary array, rgbframe , min areas for object
        # (np.array np.uint8 1channel) -> int, np.array
        # Return the biggest contourarea and contour itself
        
        #image conversion
        frame_contours = cv2.dilate(thresholded_roiframe, None) #make white areas more visible
        contours, hierarchy = cv2.findContours(frame_contours, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # find all the contours on the frame and select the biggest
        #init some variables
        self.contourareamax = 0
        maxcontour = 0
        contourarea = 0
        maxcontourrect = -1,0,0,0
        greenpixels = False
        secondmaxcontour = 0
        secondmaxcontourrect = -1,0,0,0
        self.secondcontourareamax = 0
        for i in contours:
            contourarea = cv2.contourArea(i)
            if self.target[0] == 'b':
                if contourarea > 2 and contourarea > self.secondcontourareamax and contourarea > area: # just to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if  greenpixels == True:
                        if  contourarea > self.contourareamax:
                            secondmaxcontour = maxcontour
                            secondmaxcontourrect = maxcontourrect
                            self.secondcontourareamax = self.contourareamax
                            maxcontour = i
                            maxcontourrect =  retval3[0], retval3[1], b1, b2
                            self.contourareamax = contourarea
                        else:
                            secondmaxcontour = i
                            secondmaxcontourrect = retval3[0], retval3[1], b1, b2
                            self.secondcontourareamax = contourarea
            else:
                 if contourarea > 2 and contourarea > self.contourareamax and contourarea > area: # just to eliminate random dots
                    retval3 = cv2.boundingRect(i)
                    b1 = retval3[0] + retval3[2]
                    b2 = retval3[1] +  retval3[3]
                    # check for green arount the object
                    greenpixels = self.check_for_green_pixels(retval3[0], retval3[1] , b1, b2, roiframelocal, thresholded_roiframe)
                    if greenpixels == True:
                        maxcontour = i
                        self.contourareamax = contourarea
                        maxcontourrect =  retval3[0], retval3[1], b1, b2
        #finding the biggest area e.g. find center point when the biggest contour is bigger then area defined
        if maxcontourrect[0] != -1 and self.target[0] == 'b':
            # find the center point of the first blob
            M = cv2.moments(maxcontour)
            self.x,self.y = int(M['m10']/M['m00']) + self.distancex, int(M['m01']/M['m00']) + self.distancey
            
            # second ball only if it exists
            if secondmaxcontourrect[0] != -1:
                #find second blobs center
                N = cv2.moments(secondmaxcontour)
                self.x2,self.y2 = int(N['m10']/N['m00']) + self.distancex, int(N['m01']/N['m00']) + self.distancey
            if self.debug:
                cv2.circle(self.frame,(self.x,self.y),5,(255,0,0),5)
                cv2.rectangle(self.frame, (maxcontourrect[0] + self.distancex, maxcontourrect[1] + self.distancey), (maxcontourrect[2] + self.distancex,maxcontourrect[3]+ self.distancey), (255, 0, 0)) # the biggest contour is a red rectangle                    
                if secondmaxcontourrect[0] != -1:
                    cv2.circle(self.frame,(self.x2+ self.distancex,self.y2+ self.distancey),2,(255,0,0),2)
                    cv2.rectangle(self.frame, (secondmaxcontourrect[0] + self.distancex, secondmaxcontourrect[1] + self.distancey), (secondmaxcontourrect[2]+ self.distancex,secondmaxcontourrect[3]+ self.distancey), (255,0, 0)) # the biggest contour is a red rectangle                    
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG(roiframelocal)
        
        elif maxcontourrect[0] != -1:
            self.rectx, self.recty, self.rectx2, self.recty2 = maxcontourrect[0], maxcontourrect[1], maxcontourrect[2],maxcontourrect[3]
            #finding the biggest area e.g. find center point when the biggest contour is bigger then area defined
            if self.debug:
                cv2.rectangle(roiframelocal, (maxcontourrect[0] + self.distancex, maxcontourrect[1] + self.distancey), (maxcontourrect[2] + self.distancex,maxcontourrect[3]+ self.distancey), (255, 0, 0)) # the biggest contour is a red rectangle                    
                if secondmaxcontourrect[0] != -1:
                    cv2.circle(roiframelocal,(self.x2,self.y2),5,(255,0,0),5)
                    cv2.rectangle(roiframelocal, (secondmaxcontourrect[0], secondmaxcontourrect[1]), (secondmaxcontourrect[2],secondmaxcontourrect[3]), (255,0, 0)) # the biggest contour is a red rectangle                    
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG(roiframelocal)
            self.rectx, self.recty, self.rectx2, self.recty2 = maxcontourrect
            if self.debug:
                cv2.rectangle(roiframelocal, (maxcontourrect[0], maxcontourrect[1]), (maxcontourrect[2],maxcontourrect[3]), (255, 0, 0)) # the biggest contour is a red rectangle                    
                self.thresholded_object_frame = thresholded_roiframe
                self.DEBUG(roiframelocal)
        if self.debug:
            self.thresholded_object_frame = thresholded_roiframe
            self.DEBUG(roiframelocal)


'''



