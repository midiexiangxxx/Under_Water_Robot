# -*- coding: utf-8 -*-
import cv2
import numpy as np
import serial
import sys

import time

font = cv2.FONT_HERSHEY_SIMPLEX
# cap = cv2.VideoCapture(1)  # 指定摄像头设备
# red
r_low_hsv1 = np.array([156, 43, 46])
r_high_hsv1 = np.array([180, 255, 255])
r_low_hsv2 = np.array([0, 43, 46])
r_high_hsv2 = np.array([10, 255, 255])
# green
g_low_hsv1 = np.array([35, 43, 46])
g_high_hsv1 = np.array([77, 255, 255])
# blue
b_low_hsv1 = np.array([100, 43, 46])
b_high_hsv1 = np.array([124, 255, 255])

#cap2 = cv2.VideoCapture(1)
cap2 = cv2.VideoCapture(0)


##-----------------------------------------------------------
class PID():
	def __init__(self, max, min, Kp, Kd, Ki):
		self.max = max  # 操作变量最大值
		self.min = min  # 操作变量最小值
		self.Kp = Kp         # 比例增益
		self.Kd = Kd         # 积分增益
		self.Ki = Ki         # 微分增益
		self.integral = 0    # 直到上一次的误差值
		self.pre_error = 0   # 上一次的误差值
 
	def calculate(self, setPoint, pv):
		error = setPoint - pv           # 误差
		Pout = self.Kp * error          # 比例项
		self.integral += error
		Iout = self.Ki * self.integral  # 积分项
		derivative = error - self.pre_error
		Dout = self.Kd * derivative     # 微分项
 
		output = Pout + Iout + Dout     # 新的目标值
 
		if(output > self.max):
			output = self.max
		elif(output < self.min):
			output = self.min
 
		self.pre_error = error         # 保存本次误差，以供下次计算
		return output


##-----------------------------------------------------------


###########  PWM   ##########
class V_CONTROL:
    def __init__(self, max_to_1500, max_of_acc, feed):
        self.max_to_1500 = max_to_1500
        self.max_of_acc = max_of_acc
        self.feed = feed
        self.last_pwm = 1500
        
    def percent2str(self, vin):
        vin_feed_mul = vin * self.feed
        if vin_feed_mul > 100:
            vin_feed_mul = 100
        elif vin_feed_mul < -100:
            vin_feed_mul = -100
            
        now_pwm = int(1500 + (self.max_to_1500 * vin_feed_mul / 100))
        if now_pwm - self.last_pwm > self.max_of_acc:
            now_pwm = self.last_pwm + self.max_of_acc
        elif self.last_pwm - now_pwm > self.max_of_acc:
            now_pwm = self.last_pwm - self.max_of_acc
            
        self.last_pwm = now_pwm
        return str(now_pwm)

################

def get_track():
    global cap2, r_low_hsv1, r_high_hsv1, r_low_hsv2, r_high_hsv2
    while True:
        try:
            success, img = cap2.read()
            # 颜色转换函数 转换为hsv cv2.COLOR_BGR2HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            # mask是只突出指定颜色的图片
            mask1 = cv2.inRange(hsv, lowerb=r_low_hsv1, upperb=r_high_hsv1)
            mask2 = cv2.inRange(hsv, lowerb=r_low_hsv2, upperb=r_high_hsv2)
            mask = mask1 + mask2
            # 中值滤波降噪
            median = cv2.medianBlur(mask, 5)
            """
            ---
            contours返回轮廓的点集
            ---
            hierachy返回N*4的矩阵， N表示轮廓个数
                    
            第一个数：表示同一级轮廓的下个轮廓的编号，如果这一级轮廓没有下一个轮廓，一般是这一级轮廓的最后一个的时候，则为-1

            第二个数：表示同一级轮廓的上个轮廓的编号，如果这一级轮廓没有上一个轮廓，一般是这一级轮廓的第一个的时候，则为-1

            第三个数：表示该轮廓包含的下一级轮廓的第一个的编号，假如没有，则为-1

            第四个数： 表示该轮廓的上一级轮廓的编号，假如没有上一级，则为-1

            """
            contours, hierarchy = cv2.findContours(median, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            #  cv2.RETR_EXTERNAL 只寻找最高级轮廓，即最外面的轮廓
            if len(contours) != 0:
                area = []
                # 找到最大的轮廓
                for k in range(len(contours)):
                    # contourArea面积计算
                    area.append(cv2.contourArea(contours[k]))

                # 面积最大轮廓的索引
                max_idx = np.argmax(np.array(area))

                # 生成最小的外界矩形
                rect = cv2.minAreaRect(contours[max_idx])
                """
                rect[0]返回矩形的中心点，（x,y），实际上为y行x列的像素点
                
                rect[1]返回矩形的长和宽，顺序一定不要弄错了
                
                rect[2]返回矩形的旋转角度
                
                旋转角度θ是水平轴（x轴）逆时针旋转，直到碰到矩形的第一条边停住，此时该边与水平轴的夹角。并且这个边的边长是width，另一条边边长是height。也就是说，在这里，width与height不是按照长短来定义的。
                angel是由x轴逆时针转至W(宽)的角度。
                 角度范围是[-90,0) 
                """
                # boxPoints返回四个点坐标
                box = cv2.boxPoints(rect)
                box = np.int0(box)  # 将坐标规范化为整数

                # 在opencv的坐标体系下，纵坐标最小的是top_point，纵坐标最大的是bottom_point， 横坐标最小的是left_point，横坐标最大的是right_point
                # 获取四个顶点坐标
                left_point_x = np.min(box[:, 0])
                right_point_x = np.max(box[:, 0])
                top_point_y = np.min(box[:, 1])
                bottom_point_y = np.max(box[:, 1])
                left_point_y = box[:, 1][np.where(box[:, 0] == left_point_x)][0]
                right_point_y = box[:, 1][np.where(box[:, 0] == right_point_x)][0]
                top_point_x = box[:, 0][np.where(box[:, 1] == top_point_y)][0]
                bottom_point_x = box[:, 0][np.where(box[:, 1] == bottom_point_y)][0]
                # 即获得矩形框四个点在opencv坐标体系下的各个点的值
                cv2.drawContours(img, [box], 0, (255, 0, 0), 3)
##_----------------------------------------------------------
                if bottom_point_x - left_point_x == 0 or bottom_point_x - right_point_x == 0:
                    tmp_angle = 0
                elif (bottom_point_x - left_point_x) * (bottom_point_x - left_point_x) + \
                        (bottom_point_y - left_point_y) * (bottom_point_y - left_point_y) < \
                        (bottom_point_x - right_point_x) * (bottom_point_x - right_point_x) + \
                        (bottom_point_y - right_point_y) * (bottom_point_y - right_point_y):
                    tmp_angle = int(-rect[2])
                else:
                    tmp_angle = int(-rect[2] + 90)

                tmp_x = 320 + int(np.tan(tmp_angle / 180 * np.pi) * (-160 + rect[0][1]) + rect[0][0])
                cv2.circle(img, (tmp_x, 160), 3, (0, 255, 0), 5)
                cv2.line(img, (tmp_x, 160), (320, 160), (0, 0, 255), 5)
                cv2.putText(img, str(320 - tmp_x) + ',' + str(tmp_angle), (320, 120), font, 1, (0, 0, 255), 2)
##_-----------------------------------------------------------
                cv2.imshow('img', img)
                cv2.imshow('median', median)
               
            else:
                cv2.imshow('img', img)
                cv2.imshow('median', median)
                return None

        except:
            pass


def get_ball():
    global cap1, g_low_hsv1, g_high_hsv1
    while True:
        try:
            success, img = cap1.read()
            blank = np.ones((img.shape[0], img.shape[1]), dtype=np.uint8)  # random.random()方法后面不能加数据类型
            # img = np.random.random((3,3)) #生成随机数都是小数无法转化颜色,无法调用cv2.cvtColor函数
            blank[0, 0] = 255
            blank[0, 1] = 255
            blank[0, 2] = 255
            blank1 = cv2.cvtColor(blank, cv2.COLOR_GRAY2BGR)
            # 颜色转换函数 转换为hsv cv2.COLOR_BGR2HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # mask是只突出指定颜色的图片
            mask1 = cv2.inRange(hsv, lowerb=g_low_hsv1, upperb=g_high_hsv1)
            mask = mask1

            # 中值滤波降噪
            median = cv2.medianBlur(mask, 5)
            contours, hierarchy = cv2.findContours(median, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) != 0:
                area = []
                # 找到最大的轮廓
                for k in range(len(contours)):
                    area.append(cv2.contourArea(contours[k]))
                max_idx = np.argmax(np.array(area))

                rect = cv2.minAreaRect(contours[max_idx])
                box = cv2.boxPoints(rect)
                box = np.int0(box)  # 将坐标规范化为整数
                # 绘制矩形
                if abs(rect[1][0] - rect[1][1]) > 0.3 * min(rect[1][0], rect[1][1]):
                    blank2 = blank1
                    return None
                else:
                    # 画出边缘
                    blank1 = cv2.drawContours(blank1, contours, max_idx, (255, 255, 255), cv2.FILLED)
                    blank2 = cv2.cvtColor(blank1, cv2.COLOR_BGR2GRAY)
                    circles = cv2.HoughCircles(blank2, cv2.HOUGH_GRADIENT, 2, 100, param1=100, param2=40, minRadius=10,
                                               maxRadius=200)
                    if circles is not None:  # 如果识别出圆
                        for circle in circles[0]:
                            #  获取圆的坐标与半径
                            x = int(circle[0])
                            y = int(circle[1])
                            r = int(circle[2])
                        return [x, y, r]
                    else:
                        return None
        except:
            pass


def get_rect():
    global cap1, b_low_hsv1, b_high_hsv1
    while True:
        try:
            success, img = cap1.read()
            # 颜色转换函数 转换为hsv cv2.COLOR_BGR2HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            # mask是只突出指定颜色的图片
            mask1 = cv2.inRange(hsv, lowerb=b_low_hsv1, upperb=r_high_hsv1)
            mask = mask1
            # 中值滤波降噪
            median = cv2.medianBlur(mask, 5)

            contours, hierarchy = cv2.findContours(median, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) != 0:
                area = []
                # 找到最大的轮廓
                for k in range(len(contours)):
                    area.append(cv2.contourArea(contours[k]))
                max_idx = np.argmax(np.array(area))

                rect = cv2.minAreaRect(contours[max_idx])
                return [int(rect[0][0]), int(rect[0][1])]
            else:
                return None
        except:
            pass


##----------------------------------------------------
vfeed_1 = 1
vfeed_2 = 1
vfeed_3 = 1
vfeed_4 = 1
vfeed_5 = 1
vfeed_6 = 1
v_z = 0
v_x = 0 
v_y = 0
v_p = 0
max_to_1500 = 50
max_of_acc = 5

v1 = V_CONTROL(max_to_1500, max_of_acc, vfeed_1)
v2 = V_CONTROL(max_to_1500, max_of_acc, vfeed_2)
v3 = V_CONTROL(max_to_1500, max_of_acc, vfeed_3)
v4 = V_CONTROL(max_to_1500, max_of_acc, vfeed_4)
v5 = V_CONTROL(max_to_1500, max_of_acc, vfeed_5)
v6 = V_CONTROL(max_to_1500, max_of_acc, vfeed_6)

##----------------------------------------------------
line_pid = PID(100, -100, 1, 0, 0)


##----------------------------------------------------


text = sys.argv[1]
ser = serial.Serial("/dev/ttyAMA1", 115200, timeout=0.5)
ser.write((text+'\r\n').encode())
print('input:',text)


if cap2.isOpened():
    while True:
        track_res = get_track()
        #print(track_res)
        
        #if track_res != None:
        
            #v_p = line_pid.calculate(0, track_res)
        
        str1 = v1.percent2str(v_z)
        str2 = v2.percent2str(v_z)
        str3 = v3.percent2str(v_x + v_y + v_p)
        str4 = v4.percent2str(v_x - v_y - v_p)
        str5 = v5.percent2str(v_x + v_y - v_p)
        str6 = v6.percent2str(v_x - v_y + v_p)
        #print((str(track_res) + ',' + str1 + ',' + str2 + ',' + str3 + ',' + str4 + ',' + str5 + ',' + str6).encode())

        ser.write(('0,0,' + str1 + ',' + str2 + ',' + str3 + ',' + str4 + ',' + str5 + ',' + str6).encode())
        
        if cv2.waitKey(1) & 0xff == ord('q'):
            break
else:
    print("error open cap2 failed")