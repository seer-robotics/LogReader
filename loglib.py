import re
import numpy as np
import math
from datetime import datetime

OLD_IMU_FLAG = False

def rbktimetodate(rbktime):
    """ 将rbk的时间戳转化为datatime """
    return datetime.strptime(rbktime, '%Y-%m-%d %H:%M:%S.%f')

def findrange(ts, t1, t2):
    """ 在ts中寻找大于t1小于t2对应的下标 """
    small_ind = -1
    large_ind = len(ts)-1
    for i, data in enumerate(ts):
        large_ind = i
        if(t1 < data and small_ind < 0):
            small_ind = i
        if(t2 < data):
            break
    return small_ind, large_ind

def polar2xy(angle, dist):
    """ 将极坐标angle,dist 转化为xy坐标 """
    x , y = [], []
    for a, d in zip(angle, dist):
        x.append(d * math.cos(a))
        y.append(d * math.sin(a))
    return x,y

class ReadLog:
    """ 读取Log """
    def __init__(self, *argv):
        """ 支持传入多个文件名称"""
        self.filenames = argv
    def parse(self,*argv):
        """依据输入的正则进行解析"""
        line_num = 0
        for file in self.filenames:
            for line in open(file, encoding = "utf-8"): 
                line_num += 1
                for data in argv:
                    data.parse(line)

class MCLoc:
    """  融合后的激光定位
    data[0]: t
    data[1]: x m
    data[2]: y m
    data[3]: theta degree
    data[4]: confidence
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Location\]\[(.*?)\|(.*?)\|(.*?)\|(.*?)\|0\|0\|0\|0\]\n")
        self.data = [[] for _ in range(5)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            self.data[1].append(float(datas[1])/1000.0)
            self.data[2].append(float(datas[2])/1000.0)
            self.data[3].append(float(datas[3]))
            self.data[4].append(float(datas[4]))
    def t(self):
        return self.data[0]
    def x(self):
        return self.data[1]
    def y(self):
        return self.data[2]
    def theta(self):
        return self.data[3]
    def confidence(self):
        return self.data[4]

class IMU:
    """  陀螺仪数据
    data[0]: t
    data[1]: yaw degree
    data[2]: ts yaw的时间戳
    data[3]: ax m/s^2
    data[4]: ay m/s^2
    data[5]: az m/s^2
    data[6]: gx LSB
    data[7]: gy LSB
    data[8]: gz LSB
    data[9]: offx LSB
    data[10]: offy LSB
    data[11]: offz LSB
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[IMU\]\[(.*?)\|(\d+)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\]")
        self.data = [[] for _ in range(12)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            self.data[1].append(float(datas[1])/math.pi * 180.0)
            self.data[2].append(float(datas[2]))
            self.data[3].append(float(datas[3]))
            self.data[4].append(float(datas[4]))
            self.data[5].append(float(datas[5]))
            if OLD_IMU_FLAG:
                self.data[6].append(float(datas[6])/math.pi*180.0*16.4)
                self.data[7].append(float(datas[7])/math.pi*180.0*16.4)
                self.data[8].append(float(datas[8])/math.pi*180.0*16.4)
            else:
                self.data[6].append(float(datas[6]))
                self.data[7].append(float(datas[7]))
                self.data[8].append(float(datas[8]))
            self.data[9].append(float(datas[9]))
            self.data[10].append(float(datas[10]))
            self.data[11].append(float(datas[11]))
    def t(self):
        return self.data[0]
    def yaw(self):
        return self.data[1]
    def ts(self):
        return self.data[2]
    def ax(self):
        return self.data[3]
    def ay(self):
        return self.data[4]
    def az(self):
        return self.data[5]
    def gx(self):
        return self.data[6]
    def gy(self):
        return self.data[7]
    def gz(self):
        return self.data[8]
    def offx(self):
        return self.data[9]
    def offy(self):
        return self.data[10]
    def offz(self):
        return self.data[11]

class Odometer:
    """  里程数据
    data[0]: t
    data[1]: ts 里程的时间戳
    data[2]: x m
    data[3]: y m
    data[4]: theta degree
    data[5]: stopped
    data[6]: vx m/s
    data[7]: vy m/s
    data[8]: vw rad/s
    data[9]: steer_angle rad
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Odometer\]\[0\|(\d+)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\]")
        self.data = [[] for _ in range(10)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            self.data[1].append(float(datas[1]))
            self.data[2].append(float(datas[2]))
            self.data[3].append(float(datas[3]))
            self.data[4].append(float(datas[4])/math.pi * 180.0)
            self.data[5].append(bool(datas[5] == "true"))
            self.data[6].append(float(datas[6]))
            self.data[7].append(float(datas[7]))
            self.data[8].append(float(datas[8]))
            self.data[9].append(float(datas[9]))
    def t(self):
        return self.data[0]
    def ts(self):
        return self.data[1]
    def x(self):
        return self.data[2]
    def y(self):
        return self.data[3]
    def theta(self):
        return self.data[4]
    def stop(self):
        return self.data[5]
    def vx(self):
        return self.data[6]
    def vy(self):
        return self.data[7]
    def vw(self):
        return self.data[8]
    def steer_angle(self):
        return self.data[9]

class Send:
    """  发送的速度数据
    data[0]: t
    data[1]: vx m/s
    data[2]: vy m/s
    data[3]: vw rad/s
    data[4]: steer_angle rad
    data[5]: max_vx m/s
    data[6]: max_vw rad/s
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].* \[Send\]\[(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\]')
        self.data = [[] for _ in range(7)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            self.data[1].append(float(datas[1]))
            self.data[2].append(float(datas[2]))
            self.data[3].append(float(datas[3]))
            self.data[4].append(float(datas[4]))
            self.data[5].append(float(datas[5]))
            self.data[6].append(float(datas[6]))
    def t(self):
        return self.data[0]
    def vx(self):
        return self.data[1]
    def vy(self):
        return self.data[2]
    def vw(self):
        return self.data[3]
    def steer_angle(self):
        return self.data[4]
    def max_vx(self):
        return self.data[5]
    def max_vw(self):
        return self.data[6]

class Get:
    """  接收的速度数据
    data[0]: t
    data[1]: vx m/s
    data[2]: vy m/s
    data[3]: vw rad/s
    data[4]: steer_angle rad
    data[5]: max_vx m/s
    data[6]: max_vw rad/s
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].* \[Get\]\[(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\|(.*?)\]')
        self.data = [[] for _ in range(7)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            self.data[1].append(float(datas[1]))
            self.data[2].append(float(datas[2]))
            self.data[3].append(float(datas[3]))
            self.data[4].append(float(datas[4]))
            self.data[5].append(float(datas[5]))
            self.data[6].append(float(datas[6]))
    def t(self):
        return self.data[0]
    def vx(self):
        return self.data[1]
    def vy(self):
        return self.data[2]
    def vw(self):
        return self.data[3]
    def steer_angle(self):
        return self.data[4]
    def max_vx(self):
        return self.data[5]
    def max_vw(self):
        return self.data[6]

class Laser:
    """  激光雷达的数据
    data[0]: t
    data[1]: ts 激光点的时间戳
    data[2]: angle rad 
    data[3]: dist m
    data[4]: x m
    data[5]: y m
    """
    def __init__(self, max_dist):
        """ max_dist 为激光点的最远距离，大于此距离激光点无效"""
        self.regex = re.compile('\[(.*?)\].* \[Laser\]\[(.*?)\]')
        self.data = [[] for _ in range(6)]
        self.max_dist = max_dist
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            tmp_datas = datas[1].split('|')
            self.data[1].append(float(tmp_datas[0]))
            #min_angle = float(tmp_datas[1])
            #max_angle = float(tmp_datas[2])
            #step_angle = float(tmp_datas[3])
            #data_number = int((max_angle - min_angle) / step_angle)
            angle = [float(tmp)/180.0*math.pi for tmp in tmp_datas[4::2]]
            dist = [float(tmp) for tmp in tmp_datas[5::2]]
            tmp_a, tmp_d = [], []
            for a, d in zip(angle,dist):
                if d < self.max_dist:
                    tmp_a.append(a)
                    tmp_d.append(d)
            angle = tmp_a 
            dist = tmp_d
            self.data[2].append(angle)
            self.data[3].append(dist)
            x , y = polar2xy(angle, dist)
            self.data[4].append(x)
            self.data[5].append(y)
    def t(self):
        return self.data[0]
    def ts(self):
        return self.data[1]
    def angle(self):
        return self.data[2]
    def dist(self):
        return self.data[3]
    def x(self):
        return self.data[4]
    def y(self):
        return self.data[5]

class ErrorLine:
    """  错误信息
    data[0]: t
    data[1]: 错误信息内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[error\].*")
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1]

class WarningLine:
    """  报警信息
    data[0]: t
    data[1]: 报警信息内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[warning\].*")
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1]

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider,RadioButtons
    mcl = MCLoc()
    imu = IMU()
    odo = Odometer()
    send = Send()
    get = Get()
    laser = Laser(1000.0)
    err = ErrorLine()
    war = WarningLine()
    log = ReadLog("test.log")
    log.parse(mcl, imu, odo, send, get, laser, err, war)

    print(len(err.content()), " ERRORs:")
    print(err.content())
    print(len(war.content()), " WARNINGs:")
    print(war.content())

    plt.figure(1)
    plt.subplot(4,1,1)
    plt.title('MCLoc')
    plt.plot(mcl.t(), mcl.x(),'.', label = 'x')
    plt.legend()
    plt.subplot(4,1,2)
    plt.plot(mcl.t(), mcl.y(),'.', label = 'y')
    plt.legend()
    plt.subplot(4,1,3)
    plt.plot(mcl.t(), mcl.theta(),'.', label = 'theta')
    plt.legend()
    plt.subplot(4,1,4)
    plt.plot(mcl.t(), mcl.confidence(),'.', label = 'confidence')
    plt.legend()

    plt.figure(21)
    plt.title('IMU Yaw')
    plt.plot(imu.t(), imu.yaw(),'.')
    plt.figure(2)
    plt.subplot(3,3,1)
    plt.title('IMU')
    plt.plot(imu.t(), imu.ax(),'.', label = 'ax')
    plt.legend()
    plt.subplot(3,3,2)
    plt.plot(imu.t(), imu.ay(),'.', label = 'ay')
    plt.legend()
    plt.subplot(3,3,3)
    plt.plot(imu.t(), imu.az(),'.', label = 'az')
    plt.legend()
    plt.subplot(3,3,4)
    plt.plot(imu.t(), imu.gx(),'.', label = 'gx')
    plt.legend()
    plt.subplot(3,3,5)
    plt.plot(imu.t(), imu.gy(),'.', label = 'gy')
    plt.legend()
    plt.subplot(3,3,6)
    plt.plot(imu.t(), imu.gz(),'.', label = 'gz')
    plt.legend()
    plt.subplot(3,3,7)
    plt.plot(imu.t(), imu.offx(),'.', label = 'offx')
    plt.legend()
    plt.subplot(3,3,8)
    plt.plot(imu.t(), imu.offy(),'.', label = 'offy')
    plt.legend()
    plt.subplot(3,3,9)
    plt.plot(imu.t(), imu.offz(),'.', label = 'offz')
    plt.legend()

    plt.figure(3)
    plt.subplot(2,3,1)
    plt.title('Odometer')
    plt.plot(odo.t(), odo.x(),'.', label = 'x')
    plt.legend()
    plt.subplot(2,3,2)
    plt.plot(odo.t(), odo.y(),'.', label = 'y')
    plt.legend()
    plt.subplot(2,3,3)
    plt.plot(odo.t(), odo.theta(),'.', label = 'theta')
    plt.legend()
    plt.subplot(2,3,4)
    plt.plot(odo.t(), odo.vx(),'.', label = 'vx')
    plt.legend()
    plt.subplot(2,3,5)
    plt.plot(odo.t(), odo.vy(),'.', label = 'vy')
    plt.legend()
    plt.subplot(2,3,6)
    plt.plot(odo.t(), odo.vw(),'.', label = 'vw')
    plt.legend()

    plt.figure(4)
    plt.subplot(2,2,1)
    plt.title('Send And Get Velocity')
    plt.plot(send.t(), send.vx(), 'o', label= 'send vx')
    plt.plot(get.t(), get.vx(), '.', label= 'get vx')
    plt.plot(send.t(), send.max_vx(), 'o', label= 'send max vx')
    plt.plot(get.t(), get.max_vx(), '.', label= 'get max vx')
    plt.legend()
    plt.subplot(2,2,2)
    plt.plot(send.t(), send.vy(), 'o', label= 'send vy')
    plt.plot(get.t(), get.vy(), '.', label= 'get vy')
    plt.legend()
    plt.subplot(2,2,3)
    plt.plot(send.t(), send.vw(), 'o', label= 'send vw')
    plt.plot(get.t(), get.vw(), '.', label= 'get vw')
    plt.plot(send.t(), send.max_vw(), 'o', label= 'send max vw')
    plt.plot(get.t(), get.max_vw(), '.', label= 'get max vw')
    plt.legend()
    plt.subplot(2,2,4)
    plt.plot(send.t(), send.steer_angle(), 'o', label= 'send steer_angle')
    plt.plot(get.t(), get.steer_angle(), '.', label= 'get steer_angle')
    plt.legend()

    plt.figure(5)
    plt.subplot(2,1,1)
    plt.title("Laser")
    plt.subplots_adjust(bottom=0.2,left=0.1) 
    l1, = plt.plot(laser.x()[1], laser.y()[1], '.')
    plt.axis('equal')
    plt.grid()
    plt.subplot(2,1,2,projection = 'polar')
    plt.subplots_adjust(bottom=0.2,left=0.1) 
    l2, = plt.plot(laser.angle()[1], laser.dist()[1], '.')
    axcolor = 'lightgoldenrodyellow'  # slider的颜色
    om1= plt.axes([0.1, 0.08, 0.8, 0.02], facecolor=axcolor) # 第一slider的位置
    som1 = Slider(om1, r'Time', 0, len(laser.ts())-1, valinit=0, valfmt='%i') #产生第二slider
    print(len(laser.ts()))
    def update(val):
        s1 = int(som1.val)
        l1.set_xdata(laser.x()[s1])
        l1.set_ydata(laser.y()[s1])
        l2.set_xdata(laser.angle()[s1])
        l2.set_ydata(laser.dist()[s1])
    som1.on_changed(update)
    plt.show()