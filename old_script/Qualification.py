import qi
import argparse
import time
import math
from functools import partial
import numpy as np
#import motion as mot

# Python Image Library
from PIL import Image
# OpenCV Libraries
import cv2
time_lag1=1.0*0.5
time_lag2=0.2*0.5
class HaarClassifier():
    def __init__(self,classifier_dir = 'ball_cascade.xml',
                 haar_params=(1.3,5),scale_factor = 1):
        '''
        integer scale factor > 3 (4 or above) didn't lead to correct detection
        Average prediction time with scale factor 3 (on my computer) is 0.03 sec
        '''
        self.haar_classifier = cv2.CascadeClassifier(classifier_dir)
        self.haar_params = haar_params
        self.scale_factor = scale_factor
    def predict_onimage(self,image,save_image=False, save_dir = 'DETECTED_BALL.jpg',print_=False):
        try:
            image1 = cv2.resize(image, 
                    (image.shape[0]//self.scale_factor,
                     image.shape[1]//self.scale_factor))
            image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        except:
            if print_:
                print('No image received')
                #raise Exception
            return None
        try:
            balls = self.haar_classifier.detectMultiScale(
                    image1, self.haar_params[0],self.haar_params[1])
            print(balls)
            balls = self.scale_factor*balls
        except:
            if print_:
                print('Exception while applying cascade')
                #raise Exception
            return None
        for (x,y,w,h) in balls:
            image1 = cv2.rectangle(image1, (x,y),(x+w,y+h),(255,0,0),2)
        if save_image:
            cv2.imwrite(save_dir, image1)
        if len(balls)==0:
            if print_:
                print('No balls found - returning empty')
                #raise Exception
            return None
        return balls
    def predict_ballcenter(self, image):#We predict only ball center coordinates
        ball_coords=self.predict_onimage(image)
        if ball_coords is None or len(ball_coords)==0:#no ball found
            return [0,0]
        x,y,w,h = ball_coords[0]
        center_x=x+(w//2)
        center_y=y+(h//2)
        return center_x, center_y
import os
USE_CUSTOM_MODULE=True
os.chdir('/home/robocup/QUALTEST')
BallFinder = HaarClassifier('top_cascade.xml')
''' ROBOT CONFIGURATION '''
robotIP = "192.168.1.13"
ses = qi.Session()
ses.connect(robotIP)
per = qi.PeriodicTask()
motion = ses.service('ALMotion')
posture = ses.service('ALRobotPosture')
tracker = ses.service('ALTracker')
video = ses.service('ALVideoDevice')
tts = ses.service('ALTextToSpeech')
landmark = ses.service('ALLandMarkDetection')
memory = ses.service('ALMemory')
movement=None
if USE_CUSTOM_MODULE:#MovementGraph module from neighbouring repository
    movement=ses.service('MovementGraph')
    
resolution = 2    # VGA
colorSpace = 11   # RGB
trial_number = 12
path = 'trials/trial' + str(trial_number) + '/'
def move(x,y,theta,USE_CUSTOM_MODULE=USE_CUSTOM_MODULE):
    global motion,movenent
    if USE_CUSTOM_MODULE:
       movement.Move(x,y,theta)
    else:
       motion.moveTo(x,y,theta)
def set_angles(yaw=None,pitch=None,speed=0.4):
    yaw,pitch=pitch,yaw
    global motion
    #motion.angleInterpolationWithSpeed("Head", [yaw,pitch],speed)
    motion.setAngles("HeadYaw",yaw,speed)#
    motion.setAngles("HeadPitch",pitch,speed)    
# During the initial scan, take a few pictures to analize where's the ball
def take_pics(angleScan, CameraIndex):
    names = "HeadYaw"
    useSensors = False
    motionAngles = []
    maxAngleScan = angleScan
    set_angles(-maxAngleScan,0.035)
    pic(path + 'bFound0.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(0,0.035)
    pic(path + 'bFound1.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(0,0.035)
    pic(path + 'bFound2.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    centers = analyze_img2()
    return [centers, motionAngles]

# Find the ball and center its look to it, otherwise back to 0 and rotate again
def locate_ball(centers, rot_angles):
    global ses,per,motion,posture,tracker,video,tts,landmark,memory,movement
    index = numBalls(centers)
    if len(index) == 0:
        string = "I don't see the ball."
        ang = 100
        state = 0
        RF = 0
    elif len(index) == 1:
        a = index[0]
        string = "I need to get a better look at the ball."
        ang = rot_angles[a][0]
        # ang = ang.item()
        state = 1
        RF = 0
        set_angles(ang,0.035)

    else:
        string = "I see the ball."
        a = index[0]
        b = index[1]
        RF = (rot_angles[b][0] - rot_angles[a][0]) / (centers[a][1] - centers[b][1])
        ang = rot_angles[a][0] - (320 - centers[a][1])*RF
        # ang = ang.item()
        state = 2
        set_angles(ang,0.035)
    print ang
    tts.say(string)
    return [ang, state, RF]

# Move HeadYaw from [-angleScan;angleScan]
def move_head(angleScan):
    global ses,per,motion,posture,tracker,video,tts,landmark,memory,movement

    print 'moving head'
    angleLists = [[0, angleScan]]
    timeLists = [[1.0, 2.0]]
    motion.angleInterpolation("HeadYaw", angleLists, timeLists, True)

# Calculate CoM of the thresholded ball (center of the circle)
def CenterOfMassUp(image):
    
    CM = BallFinder.predict_ballcenter(image)

    return CM
def CenterOfMassDown(image):#необходимость этой функции нуждается в уточнении
    return CenterOfMassUp(image)


# Find the center of mass of the ball
def analyze_img():
    CM = []
    for i in range(0, 7):
        img = cv2.imread(path + "camImage" + str(i) + ".png")
        cm = CenterOfMassUp(img)
        CM.append(cm)
    return CM

def analyze_img2():
    CM = []
    for i in range(0, 3):
        img = cv2.imread(path + "bFound" + str(i) + ".png")
        cm = CenterOfMassUp(img)
        CM.append(cm)
    return CM

# Look if the ball is in front of the robot
def scan_area(_angleSearch, CameraIndex):
    global ses,per,motion,posture,tracker,video,tts,landmark,memory,movement

    # Search angle where angle of rotation is [-maxAngleScan;+maxAngleScan]
    names = "HeadYaw"
    useSensors = False
    motionAngles = []
    maxAngleScan = _angleSearch
    set_angles(-maxAngleScan,0.035)
    pic(path + 'camImage0.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(-2*maxAngleScan/3, 0.035)
    pic(path + 'camImage1.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(-maxAngleScan/3, 0.035)
    pic(path + 'camImage2.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(0,0.035)
    pic(path + 'camImage3.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(maxAngleScan/3, 0.035)
    pic(path + 'camImage4.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(2*maxAngleScan/3, 0.035)
    pic(path + 'camImage5.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    set_angles(maxAngleScan, 0.035)
    pic(path + 'camImage6.png', CameraIndex)
    commandAngles = motion.getAngles(names, useSensors)
    motionAngles.append(commandAngles)
    print str(commandAngles)
    centers = analyze_img()
    return [centers, motionAngles]

# Index of pictures that contains the ball
def numBalls(CM):
    """Takes in the CM list, outputs indices of frames containing balls"""
    index = []
    for i in range(len(CM)):
        if CM[i] != [0, 0]:
            index.append(i)
    return index

# Find the ball and center its look to it, otherwise back to 0 and rotate again
def rotate_center_head(centers, rot_angles):
    index = numBalls(centers)
    found = 1
    if len(index) == 0:
        string = "I don't see the ball."
        ang = 100
        found = 0
    elif len(index) == 1:
        a = index[0]
        string = "I think I see the ball."
        ang = rot_angles[a][0]
    else:
        string = "I see the ball."
        a = index[0]
        b = index[1]
        den = 3
        if len(index) < 3:
            ang = (rot_angles[b][0] + rot_angles[a][0])/2
        else:
            c = index[2]
            ang = (rot_angles[b][0] + rot_angles[a][0] + rot_angles[c][0])/3
    print ang
    set_angles(0,0.035)
    tts.say(string)
    return ang, found

# Will take 1 picture (and return it)
def pic(_name, CameraIndex):
    videoClient = video.subscribeCamera(
        "python_client", CameraIndex, resolution, colorSpace, 5)
    naoImage = video.getImageRemote(videoClient)
    video.unsubscribe(videoClient)
    # Get the image size and pixel array.
    imageWidth = naoImage[0]
    imageHeight = naoImage[1]
    array = naoImage[6]
    im = Image.frombytes("RGB", (imageWidth, imageHeight), str(array))
    print('saving image')
    im.save(_name, "PNG")

# Funtion that will look for position of the ball and return it
def initial_scan():
    state = 0
    angleSearch = 60*math.pi/180
    ang = 100

    motion.moveInit()
    camIndex = 0  # Starts with upper camera

    state = 0
    while ang == 100:
        [CC, AA] = scan_area(angleSearch, camIndex)
        print CC
        ang, found = rotate_center_head(CC, AA)
        if found == 0 and camIndex == 1:
            state = state + 1
            camIndex = 0
            move(0,0,2*math.pi/3)

        elif found == 0 and camIndex == 0:
            camIndex = 1
        if state == 3:
            tts.say('I need to move to find the ball')
            move(0.3,0,0)

            state = 0

    else:
        move(0,0,ang*7/6)
            
    pic(path + "ball_likely.png",0)
    [CC1, AA1] = take_pics(math.pi /9, camIndex)
    print CC1
    [ang, X, delta] = locate_ball(CC1, AA1)
    if ang == 100:
        camIndex = 2
    print 'Delta', delta
    print 'Ang', ang
    move(0, 0, ang*7/6)
    img=cv2.imread(path + "ball_likely.png")
    CM=CenterOfMassUp(img)
        
    return CM, delta, camIndex

def walkUp(cm, delta):
    idx = 1
    lowerFlag = 0
    print "Entering uppercam loop"
    move(0.2, 0, 0)
    while cm[0] < 420 and cm[0] > 0:
        pp = "ball_upfront"
        ext = ".png"
        im_num = path + pp+str(idx)+ext
        pic(im_num, 0)
        img = cv2.imread(im_num)
        cm = CenterOfMassUp(img)
        print cm
        if cm[0] == 0 and cm[1] == 0:
            # Scan the area with lower camera
            pic(path + 'lower.png', 1)
            img = cv2.imread(path + "lower.png")
            cm2 = CenterOfMassUp(img)
            lowerFlag = 1
            break
        else:
            alpha = (cm[1] - 320) * delta
            move(0.2, 0, alpha*7/6)
            idx = idx + 1
            continue
    if lowerFlag == 1:
        if cm2[0] == 0 and cm2[1] == 0:
            lostFlag = 1
            print 'I lost the ball'
        else:
            lostFlag = 0
            print 'I need to switch cameras'
    else:
        pic(path + 'lower.png', 1)
        img = cv2.imread(path + 'lower.png')
        cm2 = CenterOfMassUp(img)
        lostFlag = 0
    print "Exiting up loop"
    return lostFlag, cm2
    # move(0.15, 0, 0)

def walkDown(cm, delta):
    idx = 1
    pp = "ball_downfront"
    ext = ".png"
    print 'Entering lowercam loop'
    # motion.moveTo(0.2, 0, alpha*7/6)
    move(0.2, 0, 0)
    while cm[0] > 0 and cm[0] < 230:
        # motion.moveTo(0.2, 0, 0)
        im_num = path + pp+str(idx)+ext
        pic(im_num, 1)
        img = cv2.imread(im_num)
        cm = CenterOfMassUp(img)
        print im_num, cm
        if cm == [0, 0]:
            return 0, cm
        alpha = (cm[1] - 320) * delta
        move(0.2, 0, alpha*7/6)
        idx = idx + 1
    # Tilt the head so it can have a better look of the ball
    anglePitch = math.pi * 20.6 / 180
    set_angles(pitch=anglePitch)
    print 'Pitching the head'
    # The threshold of 300 is equal to a distance of 15cm from the ball
    # The robot will do a small walk of 7cm and exit the loop
    print 'Entering sub-precise with cm[0]', cm[0]
    while cm[0] >= 0  and cm[0] < 300:
        im_num = path + pp+str(idx)+ext
        pic(im_num, 1)
        img = cv2.imread(im_num)
        cm = CenterOfMassDown(img)
        print im_num, cm
        if cm == [0, 0]:
            return 0, cm
        if cm[0] < 350:
            alpha = (cm[1] - 320) * delta
            move(0.07, 0, alpha*8/6)
        else: 
            break
        idx = idx + 1
    taskComplete = 1
    return taskComplete, cm

def getReady(cm, delta):
    # The ball should be at about 10cm roughly from the ball
    # Do the correction before it starts the loop
    idx = 1
    pp = "ball_precise"
    ext = ".png"
    im_num = path + pp+str(idx-1)+ext
    pic(im_num, 1)
    img = cv2.imread(im_num)
    cm = CenterOfMassDown(img)
    alpha = (cm[1] - 320) * delta
    move(0, 0, alpha*7/6)
    print 'Precising the position'
    print 'This is my cm[0]', cm[0]
    while cm[0] < 370:
        print 'Entering the loop'
        im_num = path + pp+str(idx)+ext
        pic(im_num, 1)
        img = cv2.imread(im_num)
        cm = CenterOfMassDown(img)
        print im_num, cm
        if cm == [0, 0]:
            return 0, cm
        if cm[0] < 405:
            alpha = (cm[1] - 320) * delta
            move(0.05, 0, alpha)
        else:
            break
        idx = idx + 1
    return 1
    # This should exit at a good distance to kick the ball

def kickBall(mode='right'):
    if USE_CUSTOM_MODULE:
        if mode=='right':
            return movement.KickRight()
        else:
            return movement.KickLeft()
    # Activate Whole Body Balancer
    isEnabled  = True
    motion.wbEnable(isEnabled)

    # Legs are constrained fixed
    stateName  = "Fixed"
    supportLeg = "Legs"
    motion.wbFootState(stateName, supportLeg)

    # Constraint Balance Motion
    isEnable   = True
    supportLeg = "Legs"
    motion.wbEnableBalanceConstraint(isEnable, supportLeg)

    # Com go to LLeg
    supportLeg = "LLeg"
    duration   = 1.0
    motion.wbGoToBalance(supportLeg, duration)

    # RLeg is free
    stateName  = "Free"
    supportLeg = "RLeg"
    motion.wbFootState(stateName, supportLeg)

    # RLeg is optimized
    effectorName = "RLeg"
    axisMask     = 63
    '''
    There was mot.FRAME_TORSO, which is equal to 0
    '''
    space        = 0#mot.FRAME_TORSO


    # Motion of the RLeg
    dx      = 0.025                 # translation axis X (meters)
    dz      = 0.02                 # translation axis Z (meters)
    dwy     = 5.0*math.pi/180.0    # rotation axis Y (radian)


    times   = [1.0, 1.4, 2.1]
    isAbsolute = False

    targetList = [
      [-0.7*dx, 0.0, 1.1*dz, 0.0, +dwy, 0.0],
      [+2.2*dx, +dx, dz, 0.0, -dwy, 0.0],
      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]

    motion.positionInterpolation(effectorName, space, targetList,
                                 axisMask, times, isAbsolute)


    # Example showing how to Enable Effector Control as an Optimization
    isActive     = False
    motion.wbEnableEffectorOptimization(effectorName, isActive)

    time.sleep(time_lag1)

    # Deactivate Head tracking
    isEnabled    = False
    motion.wbEnable(isEnabled)

    # send robot to Pose Init
    posture.goToPosture("StandInit", 0.5)

def set_head_position(_angle):
    fracSpeed = 0.2
    names = ['HeadYaw']
    motion.setAngles(names, _angle, fracSpeed)

def zero_head():
    global ses,per,motion,posture,tracker,video,tts,landmark,memory,movement
    robotIP = "192.168.1.13"
    try:
        motion.angleInterpolationWithSpeed("HeadYaw", 0, 0.1)
    except:
        ses = qi.Session()
        ses.connect(robotIP)
        per = qi.PeriodicTask()
        motion = ses.service('ALMotion')
        posture = ses.service('ALRobotPosture')
        tracker = ses.service('ALTracker')
        video = ses.service('ALVideoDevice')
        tts = ses.service('ALTextToSpeech')
        landmark = ses.service('ALLandMarkDetection')
        memory = ses.service('ALMemory')
        movement=ses.service('MovementGraph')
def main1(robotIP,port=9559):
    pass
def main(robotIP, PORT=9559,num_iter=5):

    #Wake up the robot
    motion.wakeUp()
    taskCompleteFlag = 0
    num_iter = num_iter
    i=0
    while taskCompleteFlag == 0 and i<num_iter:
        ballPosition, delta, camIndex = initial_scan()
        if camIndex == 0:
            zero_head()
            lost, CoM = walkUp(ballPosition, delta)
            if lost == 0:
                # Switch cameras
                time.sleep(time_lag2)
                video.stopCamera(0)
                video.startCamera(1)
                video.setActiveCamera(1)
                zero_head()
                # Walk to the ball using lower camera
                taskCompleteFlag, CoM1 = walkDown(CoM, delta)
                taskCompleteFlag = getReady(CoM1, delta)
            else:
                tts.say('I lost the ball, I need to rescan.')
                move(-0.2, 0, 0)
        elif camIndex == 1:
            # Switch cameras
            time.sleep(time_lag2)
            video.stopCamera(0)
            video.startCamera(1)
            video.setActiveCamera(1)
            zero_head()
            # Walk to the ball using lower camera
            taskCompleteFlag, CoM1 = walkDown(ballPosition, delta)
            taskCompleteFlag = getReady(CoM1, delta)
        i+=1
    kickBall('right')
    motion.rest()



main(robotIP)
