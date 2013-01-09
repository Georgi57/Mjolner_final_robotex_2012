Mjolner_final_robotex_2012
==========================

Code that Mjolner used  in Robotex 2012 in the first and second rounds.
Later there were some changes, but they included more bugs than useful functions.

INSTALL

This code is based on python 2.7 and to use it you have to install opencv, serialpy and wx python libraries.



USE

You can run robot main function from console (main.py) but for the rest I suggest using the GUI.py or RUN bash script.
To run the code you have to check the path in RUN bash script.
RUN bash script is used for running the program by clicking on it.
Because our robot construction made it impossible to use the notebook keyboard,
while the touchpad is accessable we introduced this method of running the program.
For the same reason we created a GUI for the robot.

Although we could use Wifi to access robot through TeamViewer,
internet connection made it almost impossible to use in the contest.



CONSISTS

Whole code consists of 6 python files, one bash script and on text file.

GUI.py - graphical interface for all robot functions

RUN - bash script for running the GUI.py, while configuring the camera

main.py - AI, main algorithm

robot_com.py - low level communication and commands

tests.py - movement, kick and manual control functions

threshold.py - configuring the color thresholds for videoprocessing 

thresholdvalues.txt - last save values of the thresholds

videoprocessing.py - videoprocessing module, which includes second robot videoprocessing also.

ALGORITHM

Essential files of the algorithm: main.py, robot_com.py, videoprocessing.py, thresholdvalues.txt.
Run the algorithm by running main.py. Algorithm consists of an infinite loop,
which includes robot sensors checking, camera image processing and action decision.  

DESCRIPTION OF ADDITIONAL FILES

GUI.py makes it possible to use all of the robot function with the mouse or the touchpad,
although they are all accessable through console.

thresholds.py file is used to configure color thresholds for our videoprocessing module.
These values are saved in thresholdvalues.txt file ot be accessed later.

tests.py is used for testin purposes like movement, kicking and manual control testing.
