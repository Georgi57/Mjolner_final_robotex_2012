import cv2.cv as cv
import cv2
import numpy as np

class ManualCalibration():
    
    def __init__(self, what_to_capture):
        #Camera
        self.cam = cv2.VideoCapture(what_to_capture)
        self.objects = "Ball/Blue gate/Yellow gate/Black/White/Green"
        self.colors = []
                
        #Create for the occasion, when there are no file
        for i in range(36):
            if i%6>=0 and i%6<3:
                self.colors.append(0)
            else:
                self.colors.append(255)
        try:
            f = open('thresholdvalues.txt',  'r')
            a = f.read()
            c=a.split()
            if len(c)==len(self.colors):
                self.colors=c
            f.close()
            print "Colors:"
        except:
            print "There was no file. Creating new values:"

        self.currentcolors = []
        for i in range(6):
            self.currentcolors.append(self.colors[0*6+i])
        print self.colors
        self.running = True

        #Interface
        cv.NamedWindow("webcam", cv.CV_WINDOW_AUTOSIZE)
        cv.NamedWindow("Thresholded", cv.CV_WINDOW_AUTOSIZE)
        cv.NamedWindow(self.objects, cv.CV_WINDOW_NORMAL)
        cv.MoveWindow('webcam', 0, 350)
        cv.MoveWindow(self.objects, 450, 0)

        cv.CreateTrackbar('object', self.objects,  0,  5, self.change_object)
        cv.CreateTrackbar('hue', self.objects,  int(self.currentcolors[0]),  255, self.save_changes)
        cv.CreateTrackbar('saturation', self.objects,  int(self.currentcolors[1]),  255,  self.save_changes)
        cv.CreateTrackbar('value', self.objects,  int(self.currentcolors[2]),  255,  self.save_changes)
        cv.CreateTrackbar('maxhue', self.objects,  int(self.currentcolors[3]),  255,  self.save_changes)
        cv.CreateTrackbar('maxsaturation', self.objects, int(self.currentcolors[4]),  255,  self.save_changes)
        cv.CreateTrackbar('maxvalue', self.objects,  int(self.currentcolors[5]),  255,  self.save_changes)

        self.change_object(0)
        

    def save_changes(self,idx):
        # Save changes made in the sliders
        obj = cv.GetTrackbarPos('object', self.objects)
        hue = cv.GetTrackbarPos('hue', self.objects)
        saturation = cv.GetTrackbarPos('saturation', self.objects)
        value = cv.GetTrackbarPos('value', self.objects)
        xhue = cv.GetTrackbarPos('maxhue', self.objects)
        xsaturation = cv.GetTrackbarPos('maxsaturation', self.objects)
        xvalue = cv.GetTrackbarPos('maxvalue', self.objects)
        
        self.currentcolors=[hue,saturation,value,xhue,xsaturation,xvalue]
        self.colors[int(obj)*6:(int(obj)+1)*6]=self.currentcolors[:]
        
        string=""
        for i in self.colors:
            string+=str(i)+" "
        f = open('thresholdvalues.txt',  'w')
        f.write(string)
        f.close()

    def change_object(self,idx):
        currentcolors = []
        obj = cv.GetTrackbarPos('object', self.objects)
        for i in range(6):
            currentcolors.append(self.colors[obj*6+i])
        
        cv.SetTrackbarPos('hue', self.objects, int(currentcolors[0]))
        cv.SetTrackbarPos('saturation', self.objects, int(currentcolors[1]))
        cv.SetTrackbarPos('value', self.objects, int(currentcolors[2]))
        cv.SetTrackbarPos('maxhue', self.objects, int(currentcolors[3]))
        cv.SetTrackbarPos('maxsaturation', self.objects, int(currentcolors[4]))
        cv.SetTrackbarPos('maxvalue', self.objects, int(currentcolors[5]))
        self.currentcolors=currentcolors[:]
    def main(self):
        #Get camera frame
        
        retval, frame = self.cam.read()
        obj = cv.GetTrackbarPos('object', self.objects)
        #self.save_changes(obj)
        self.currentcolors = []
        for i in range(6):
            self.currentcolors.append(self.colors[obj*6+i])
        minrange = np.asarray([self.currentcolors[0], self.currentcolors[1], self.currentcolors[2]], np.uint8)
        maxrange = np.asarray([self.currentcolors[3], self.currentcolors[4], self.currentcolors[5]], np.uint8)
        if obj == 3 or obj == 4:
            thresholded_frame = cv2.inRange(frame, minrange, maxrange)
            cv2.dilate(thresholded_frame, None)
        else:
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            thresholded_frame = cv2.inRange(hsv_frame, minrange, maxrange)
            cv2.dilate(thresholded_frame, None)
        cv2.imshow("webcam", frame)
        cv2.imshow("Thresholded",  thresholded_frame)

    def run(self):
        while self.running:
            self.main()
            key=cv.WaitKey(100)
            if key == 27:
                self.running = False
        cv.DestroyAllWindows()
        self.cam.release()

    def stop(self):
        self.running = False

if __name__ == "__main__":
    CV = ManualCalibration(0)
    CV.run()
