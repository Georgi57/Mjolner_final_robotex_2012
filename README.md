Mjolner_final_robotex_2012
==========================

Code that Mjolner used  in Robotex 2012 in the first and second rounds.
Later there were some changes, but they included more bugs than useful functions.

INSTALL

This code is based on python 2.7
and to use this code you have to install opencv, serialpy and wx python libraries.


USE

To run the code you have to check the path in RUN bash script.
RUN bash script is used for running the program by clicking on it.
Because our robot construction made it impossible to use the notebook keyboard,
while the touchpad is accessable we introduced this method of running the program.
For the same reason we created a GUI for the robot.

Although we could use Wifi to access robot through TeamViewer,
internet connction made it almost impossible to use in the contest.


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

main program consists of 3 .py files:

main.py - AI

robot_com.py - low level commands

videoprocessing.py - videoprocessing of camera picture

ADDITIONAL FILE DESCRIBTION

GUI.py makes it possible to use all of the robot function with the mouse or the touchpad,
although they are all accessable through console.

thresholds.py file is used to configure color thresholds for our videoprocessing module.
These values are saved in thresholdvalues.txt file ot be accessed later.

thresholdvalues.txt - last save values of the thresholds.

tests.py is used for testin purposes like movement, kicking and manual control testing.
