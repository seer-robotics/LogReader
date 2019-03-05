import re
import math
from datetime import datetime
import codecs
import chardet

def rbktimetodate(rbktime):
    """ 将rbk的时间戳转化为datatime """
    return datetime.strptime(rbktime, '%Y-%m-%d %H:%M:%S.%f')

def findrange(ts, t1, t2):
    """ 在ts中寻找大于t1小于t2对应的下标 """
    small_ind = -1
    large_ind = len(ts)-1
    for i, data in enumerate(ts):
        large_ind = i
        if(t1 <= data and small_ind < 0):
            small_ind = i
        if(t2 <= data):
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
    def __init__(self, filenames):
        """ 支持传入多个文件名称"""
        self.filenames = filenames
    def parse(self,*argv):
        """依据输入的正则进行解析"""
        line_num = 0
        for file in self.filenames:
            for line in open(file, 'rb'): 
                try:
                    line = line.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        line = line.decode('gbk')
                    except UnicodeDecodeError:
                        print("Line ",line_num+1, " is skipped due to decoding failure!", " ", line)
                        continue
                line_num += 1
                for data in argv:
                    if data.parse(line):
                        break

class MCLoc:
    """  融合后的激光定位
    data[0]: t
    data[1]: x m
    data[2]: y m
    data[3]: theta degree
    data[4]: confidence
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Location\]\[(.*?)\|(.*?)\|(.*?)\|(.*?)\|0\|0\|0\|0\]")
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
            return True
        return False
    def t(self):
        return self.data[0]
    def x(self):
        return self.data[1], self.data[0]
    def y(self):
        return self.data[2], self.data[0]
    def theta(self):
        return self.data[3], self.data[0]
    def confidence(self):
        return self.data[4], self.data[0]

class IMU:
    """  陀螺仪数据
    data[0]: t
    data[1]: yaw degree
    data[2]: pitch degree
    data[3]: roll degree
    data[4]: ts yaw的时间戳
    data[5]: ax m/s^2
    data[6]: ay m/s^2
    data[7]: az m/s^2
    data[8]: gx LSB
    data[9]: gy LSB
    data[10]: gz LSB
    data[11]: offx LSB
    data[12]: offy LSB
    data[13]: offz LSB
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[IMU\]\[(.*?)\]")
        self.data = [[] for _ in range(14)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 11:
                self.data[1].append(float(values[0])/math.pi * 180.0)
                self.data[4].append(float(values[1]))
                self.data[5].append(float(values[2]))
                self.data[6].append(float(values[3]))
                self.data[7].append(float(values[4]))
                self.data[8].append(float(values[5]))
                self.data[9].append(float(values[6]))
                self.data[10].append(float(values[7]))
                self.data[11].append(float(values[8]))
                self.data[12].append(float(values[9]))
                self.data[13].append(float(values[10]))
            elif len(values) == 13:
                self.data[1].append(float(values[0])/math.pi * 180.0)
                self.data[2].append(float(values[1])/math.pi * 180.0)
                self.data[3].append(float(values[2])/math.pi * 180.0)
                self.data[4].append(float(values[3]))
                self.data[5].append(float(values[4]))
                self.data[6].append(float(values[5]))
                self.data[7].append(float(values[6]))
                self.data[8].append(float(values[7]))
                self.data[9].append(float(values[8]))
                self.data[10].append(float(values[9]))
                self.data[11].append(float(values[10]))
                self.data[12].append(float(values[11]))
                self.data[13].append(float(values[12]))
            else:
                print("Error in IMU parse: ", datas)
            return True
        return False

    def old2newGyro(self):
        self.data[8] = [v/math.pi*180.0*16.4 for v in self.data[8]]
        self.data[9] = [v/math.pi*180.0*16.4 for v in self.data[9]]
        self.data[10] = [v/math.pi*180.0*16.4 for v in self.data[10]]

    def t(self):
        return self.data[0]
    def yaw(self):
        return self.data[1], self.data[0]
    def pitch(self):
        return self.data[2], self.data[0]
    def roll(self):
        return self.data[3], self.data[0]
    def ts(self):
        return self.data[4], self.data[0]
    def ax(self):
        return self.data[5], self.data[0]
    def ay(self):
        return self.data[6], self.data[0]
    def az(self):
        return self.data[7], self.data[0]
    def gx(self):
        return self.data[8], self.data[0]
    def gy(self):
        return self.data[9], self.data[0]
    def gz(self):
        return self.data[10], self.data[0]
    def offx(self):
        return self.data[11], self.data[0]
    def offy(self):
        return self.data[12], self.data[0]
    def offz(self):
        return self.data[13], self.data[0]

class Odometer:
    """  里程数据
    data[0]: t
    data[1]: cycle
    data[2]: ts 里程的时间戳
    data[3]: x m
    data[4]: y m
    data[5]: theta degree
    data[6]: stopped
    data[7]: vx m/s
    data[8]: vy m/s
    data[9]: vw rad/s
    data[10]: steer_angle rad
    data[11]: steer_angle rad
    data[12]: steer_angle rad
    data[13]: steer_angle rad
    data[14]: steer_angle rad
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Odometer\]\[(.*?)\]")
        self.data = [[] for _ in range(15)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) >= 10:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
                self.data[3].append(float(values[2]))
                self.data[4].append(float(values[3]))
                self.data[5].append(float(values[4])/math.pi * 180.0)
                self.data[6].append(float(values[5] == "true"))
                self.data[7].append(float(values[6]))
                self.data[8].append(float(values[7]))
                self.data[9].append(float(values[8]))
                self.data[10].append(float(values[9]))
                if len(values) >= 11:
                    self.data[11].append(float(values[10]))
                    if len(values) >= 12:
                        self.data[12].append(float(values[11]))
                        if len(values) >= 13:
                            self.data[13].append(float(values[12]))
                            if len(values) >= 14:
                                self.data[14].append(float(values[13]))
                                if len(values) >= 15:
                                    print("Error in Odometer parse: ", datas)
            else:
                print("Error in Odometer parse: ", datas)
            return True
        return False


    def t(self):
        return self.data[0]
    def cycle(self):
        return self.data[1], self.data[0]
    def ts(self):
        return self.data[2], self.data[0]
    def x(self):
        return self.data[3], self.data[0]
    def y(self):
        return self.data[4], self.data[0]
    def theta(self):
        return self.data[5], self.data[0]
    def stop(self):
        return self.data[6], self.data[0]
    def vx(self):
        return self.data[7], self.data[0]
    def vy(self):
        return self.data[8], self.data[0]
    def vw(self):
        return self.data[9], self.data[0]
    def steer_angle(self):
        return self.data[10], self.data[0]
    def encode0(self):
        return self.data[11], self.data[0]
    def encode1(self):
        return self.data[12], self.data[0]
    def encode2(self):
        return self.data[13], self.data[0]
    def encode3(self):
        return self.data[14], self.data[0]

class LaserOdometer:
    """ 激光里程数据 
    data[0]: t
    data[1]: ts  
    data[2]: x
    data[3]: y
    data[4]: angle
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].*\[LaserOdometer\]\[(.*?)\]')
        self.data = [[] for _ in range(5)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 4:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
                self.data[3].append(float(values[2]))
                self.data[4].append(float(values[3])/math.pi*180.0)
            else:
                print("Error in LaserOdometer parse: ", datas)
            return True
        return False
    def t(self):
        return self.data[0]
    def ts(self):
        return self.data[1], self.data[0]
    def x(self):
        return self.data[2], self.data[0]
    def y(self):
        return self.data[3], self.data[0]
    def angle(self):
        return self.data[4], self.data[0]

class Battery:
    """  电池数据
    data[0]: t
    data[1]: percentage  
    data[2]: current
    data[3]: voltage
    data[4]: ischarging
    data[5]: temperature
    data[6]: cycle
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].*\[Battery\]\[(.*?)\]')
        self.data = [[] for _ in range(7)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 6:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
                self.data[3].append(float(values[2]))
                self.data[4].append(float(values[3] == "true"))
                self.data[5].append(float(values[4]))
                self.data[6].append(float(values[5]))
            else:
                print("Error in Battery parse: ", datas)
            return True
        return False
    def t(self):
        return self.data[0]
    def percentage(self):
        return self.data[1], self.data[0]
    def current(self):
        return self.data[2], self.data[0]
    def voltage(self):
        return self.data[3], self.data[0]
    def ischarging(self):
        return self.data[4], self.data[0]
    def temperature(self):
        return self.data[5], self.data[0]
    def cycle(self):
        return self.data[6], self.data[0]

class Controller:
    """  控制器数据
    data[0]: t
    data[1]: temp  
    data[2]: humi
    data[3]: voltage
    data[4]: emc
    data[5]: brake
    data[6]: driveremc
    data[7]: manualcharge
    data[8]: autocharge
    data[9]: electric
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].*\[Controller\]\[(.*?)\]')
        self.data = [[] for _ in range(10)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 9:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
                self.data[3].append(float(values[2]))
                self.data[4].append(float(values[3] == "true"))
                self.data[5].append(float(values[4] == "true"))
                self.data[6].append(float(values[5] == "true"))
                self.data[7].append(float(values[6] == "true"))
                self.data[8].append(float(values[7] == "true"))
                self.data[9].append(float(values[8] == "true"))
            else:
                print("Error in Controller parse: ", datas)
            return True
        return False

    def t(self):
        return self.data[0]
    def temp(self):
        return self.data[1], self.data[0]
    def humi(self):
        return self.data[2], self.data[0]
    def voltage(self):
        return self.data[3], self.data[0]
    def emc(self):
        return self.data[4], self.data[0]
    def brake(self):
        return self.data[5], self.data[0]
    def driveremc(self):
        return self.data[6], self.data[0]
    def manualcharge(self):
        return self.data[7], self.data[0]
    def autocharge(self):
        return self.data[8], self.data[0]
    def electric(self):
        return self.data[9], self.data[0]

class StopPoints:
    """ 阻挡障碍物信息 
    data[0]: t
    data[1]: x  
    data[2]: y
    data[3]: type
    data[4]: id
    data[5]: dist
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].*\[StopPoints\]\[(.*?)\]')
        self.data = [[] for _ in range(10)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 5:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
                self.data[3].append(float(values[2]))
                self.data[4].append(float(values[3]))
                self.data[5].append(float(values[4]))
            else:
                print("Error in StopPoints parse: ", datas)
            return True
        return False

    def t(self):
        return self.data[0]
    def x(self):
        return self.data[1], self.data[0]
    def y(self):
        return self.data[2], self.data[0]
    def type(self):
        return self.data[3], self.data[0]
    def id(self):
        return self.data[4], self.data[0]
    def dist(self):
        return self.data[5], self.data[0]

class SlowDownPoints:
    """ 减速障碍物信息 
    data[0]: t
    data[1]: x  
    data[2]: y
    data[3]: type
    data[4]: id
    data[5]: dist
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].*\[SlowDownPoints\]\[(.*?)\]')
        self.data = [[] for _ in range(10)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 5:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
                self.data[3].append(float(values[2]))
                self.data[4].append(float(values[3]))
                self.data[5].append(float(values[4]))
            else:
                print("Error in StopPoints parse: ", datas)
            return True
        return False

    def t(self):
        return self.data[0]
    def x(self):
        return self.data[1], self.data[0]
    def y(self):
        return self.data[2], self.data[0]
    def type(self):
        return self.data[3], self.data[0]
    def id(self):
        return self.data[4], self.data[0]
    def dist(self):
        return self.data[5], self.data[0]

class SensorFuser:
    """ 传感器融合信息
    data[0]: t
    data[1]: localnum  
    data[2]: globalnum 
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].*\[SensorFuserPoints\]\[(.*?)\]')
        self.data = [[] for _ in range(10)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            datas = out.groups()
            self.data[0].append(rbktimetodate(datas[0]))
            values = datas[1].split('|')
            if len(values) == 2:
                self.data[1].append(float(values[0]))
                self.data[2].append(float(values[1]))
            else:
                print("Error in SensorFuser parse: ", datas)
            return True
        return False

    def t(self):
        return self.data[0]
    def localnum(self):
        return self.data[1], self.data[0]
    def globalnum(self):
        return self.data[2], self.data[0]

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
            return True
        return False
    def t(self):
        return self.data[0]
    def vx(self):
        return self.data[1], self.data[0]
    def vy(self):
        return self.data[2], self.data[0]
    def vw(self):
        return self.data[3], self.data[0]
    def steer_angle(self):
        return self.data[4], self.data[0]
    def max_vx(self):
        return self.data[5], self.data[0]
    def max_vw(self):
        return self.data[6], self.data[0]

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
            return True
        return False
    def t(self):
        return self.data[0]
    def vx(self):
        return self.data[1], self.data[0]
    def vy(self):
        return self.data[2], self.data[0]
    def vw(self):
        return self.data[3], self.data[0]
    def steer_angle(self):
        return self.data[4], self.data[0]
    def max_vx(self):
        return self.data[5], self.data[0]
    def max_vw(self):
        return self.data[6], self.data[0]

class Manual:
    """  手动的速度数据
    data[0]: t
    data[1]: vx m/s
    data[2]: vy m/s
    data[3]: vw rad/s
    data[4]: steer_angle rad
    """
    def __init__(self):
        self.regex = re.compile('\[(.*?)\].* \[Manual\]\[(.*?)\|(.*?)\|(.*?)\|(.*?)\]')
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
            return True
        return False
    def t(self):
        return self.data[0]
    def vx(self):
        return self.data[1], self.data[0]
    def vy(self):
        return self.data[2], self.data[0]
    def vw(self):
        return self.data[3], self.data[0]
    def steer_angle(self):
        return self.data[4], self.data[0]

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
            return True
        return False
    def t(self):
        return self.data[0]
    def ts(self):
        return self.data[1], self.data[0]
    def angle(self):
        return self.data[2], self.data[0]
    def dist(self):
        return self.data[3], self.data[0]
    def x(self):
        return self.data[4], self.data[0]
    def y(self):
        return self.data[5], self.data[0]

class ErrorLine:
    """  错误信息
    data[0]: t
    data[1]: 错误信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.general_regex = re.compile("\[(.*?)\].*\[error\].*")
        self.regex = re.compile("\[(.*?)\].*\[error\].*\[Alarm\]\[.*?\|(.*?)\|(.*?)\|.*")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
            new_num = out.group(2)
            if not new_num in self.data[2]:
                self.data[2].append(new_num)
                self.data[3].append(out.group(3))
            return True
        else:
            out = self.general_regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = '00000'
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)                
                    self.data[3].append('unKnown Error')
                return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]

class WarningLine:
    """  报警信息
    data[0]: t
    data[1]: 报警信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.general_regex = re.compile("\[(.*?)\].*\[warning\].*")
        self.regex = re.compile("\[(.*?)\].*\[warning\].*\[Alarm\]\[.*?\|(.*?)\|(.*?)\|.*")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
            new_num = out.group(2)
            if not new_num in self.data[2]:
                self.data[2].append(new_num)
                self.data[3].append(out.group(3))
            return True
        else:
            out = self.general_regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = '00000'
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append('unKnown Warning')
                return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]

class FatalLine:
    """  错误信息
    data[0]: t
    data[1]: 报警信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[fatal\].*\[Alarm\]\[.*?\|(.*?)\|(.*?)\|.*")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
            new_num = out.group(2)
            new_data_flag = True
            if not new_num in self.data[2]:
                self.data[2].append(new_num)
                self.data[3].append(out.group(3))
            return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]

class NoticeLine:
    """  注意信息
    data[0]: t
    data[1]: 注意信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Alarm\]\[Notice\|(.*?)\|(.*?)\|.*")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
            new_num = out.group(2)
            if not new_num in self.data[2]:
                self.data[2].append(new_num)
                self.data[3].append(out.group(3))
            return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]

class TaskStart:
    """  任务开始信息
    data[0]: t
    data[1]: 开始信息内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Text\]\[cnt:.*")
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
            return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]

class TaskFinish:
    """  任务结束信息
    data[0]: t
    data[1]: 结束信息内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Text\]\[Task finished.*")
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        out = self.regex.match(line)
        if out:
            self.data[0].append(rbktimetodate(out.group(1)))
            self.data[1].append(out.group(0))
            return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
# if __name__ == '__main__':
#     import matplotlib.pyplot as plt
#     from matplotlib.widgets import Slider,RadioButtons
#     mcl = MCLoc()
#     imu = IMU()
#     odo = Odometer()
#     send = Send()
#     get = Get()
#     laser = Laser(1000.0)
#     err = ErrorLine()
#     war = WarningLine()
#     log = ReadLog(["test1.log"])
#     log.parse(mcl, imu, odo, send, get, laser, err, war)

#     print(len(err.content()), " ERRORs:")
#     print(err.content())
#     print(len(war.content()), " WARNINGs:")
#     print(war.content())

#     plt.figure(1)
#     plt.subplot(4,1,1)
#     plt.title('MCLoc')
#     plt.plot(mcl.x()[1], mcl.x()[0],'.', label = 'x')
#     plt.legend()
#     plt.subplot(4,1,2)
#     plt.plot(mcl.y()[1], mcl.y()[0],'.', label = 'y')
#     plt.legend()
#     plt.subplot(4,1,3)
#     plt.plot(mcl.theta()[1], mcl.theta()[0],'.', label = 'theta')
#     plt.legend()
#     plt.subplot(4,1,4)
#     plt.plot(mcl.confidence()[1], mcl.confidence()[0],'.', label = 'confidence')
#     plt.legend()

#     plt.figure(21)
#     plt.title('IMU Yaw')
#     plt.plot(imu.yaw()[1], imu.yaw()[0],'.')
#     plt.figure(2)
#     plt.subplot(3,3,1)
#     plt.title('IMU')
#     plt.plot(imu.ax()[1], imu.ax()[0],'.', label = 'ax')
#     plt.legend()
#     plt.subplot(3,3,2)
#     plt.plot(imu.t(), imu.ay()[0],'.', label = 'ay')
#     plt.legend()
#     plt.subplot(3,3,3)
#     plt.plot(imu.t(), imu.az()[0],'.', label = 'az')
#     plt.legend()
#     plt.subplot(3,3,4)
#     plt.plot(imu.t(), imu.gx()[0],'.', label = 'gx')
#     plt.legend()
#     plt.subplot(3,3,5)
#     plt.plot(imu.t(), imu.gy()[0],'.', label = 'gy')
#     plt.legend()
#     plt.subplot(3,3,6)
#     plt.plot(imu.t(), imu.gz()[0],'.', label = 'gz')
#     plt.legend()
#     plt.subplot(3,3,7)
#     plt.plot(imu.t(), imu.offx()[0],'.', label = 'offx')
#     plt.legend()
#     plt.subplot(3,3,8)
#     plt.plot(imu.t(), imu.offy()[0],'.', label = 'offy')
#     plt.legend()
#     plt.subplot(3,3,9)
#     plt.plot(imu.t(), imu.offz()[0],'.', label = 'offz')
#     plt.legend()

#     plt.figure(3)
#     plt.subplot(2,3,1)
#     plt.title('Odometer')
#     plt.plot(odo.t(), odo.x()[0],'.', label = 'x')
#     plt.legend()
#     plt.subplot(2,3,2)
#     plt.plot(odo.t(), odo.y()[0],'.', label = 'y')
#     plt.legend()
#     plt.subplot(2,3,3)
#     plt.plot(odo.t(), odo.theta()[0],'.', label = 'theta')
#     plt.legend()
#     plt.subplot(2,3,4)
#     plt.plot(odo.t(), odo.vx()[0],'.', label = 'vx')
#     plt.legend()
#     plt.subplot(2,3,5)
#     plt.plot(odo.t(), odo.vy()[0],'.', label = 'vy')
#     plt.legend()
#     plt.subplot(2,3,6)
#     plt.plot(odo.t(), odo.vw()[0],'.', label = 'vw')
#     plt.legend()

#     plt.figure(4)
#     plt.subplot(2,2,1)
#     plt.title('Send And Get Velocity')
#     plt.plot(send.t(), send.vx()[0], 'o', label= 'send vx')
#     plt.plot(get.t(), get.vx()[0], '.', label= 'get vx')
#     plt.plot(send.t(), send.max_vx()[0], 'o', label= 'send max vx')
#     plt.plot(get.t(), get.max_vx()[0], '.', label= 'get max vx')
#     plt.legend()
#     plt.subplot(2,2,2)
#     plt.plot(send.t(), send.vy()[0], 'o', label= 'send vy')
#     plt.plot(get.t(), get.vy()[0], '.', label= 'get vy')
#     plt.legend()
#     plt.subplot(2,2,3)
#     plt.plot(send.t(), send.vw()[0], 'o', label= 'send vw')
#     plt.plot(get.t(), get.vw()[0], '.', label= 'get vw')
#     plt.plot(send.t(), send.max_vw()[0], 'o', label= 'send max vw')
#     plt.plot(get.t(), get.max_vw()[0], '.', label= 'get max vw')
#     plt.legend()
#     plt.subplot(2,2,4)
#     plt.plot(send.t(), send.steer_angle()[0], 'o', label= 'send steer_angle')
#     plt.plot(get.t(), get.steer_angle()[0], '.', label= 'get steer_angle')
#     plt.legend()

#     plt.figure(5)
#     plt.subplot(2,1,1)
#     plt.title("Laser")
#     plt.subplots_adjust(bottom=0.2,left=0.1) 
#     l1, = plt.plot(laser.x()[0][0], laser.y()[0][0], '.')
#     plt.axis('equal')
#     plt.grid()
#     plt.subplot(2,1,2,projection = 'polar')
#     plt.subplots_adjust(bottom=0.2,left=0.1) 
#     l2, = plt.plot(laser.angle()[0][0], laser.dist()[0][0], '.')
#     axcolor = 'lightgoldenrodyellow'  # slider的颜色
#     om1= plt.axes([0.1, 0.08, 0.8, 0.02], facecolor=axcolor) # 第一slider的位置
#     som1 = Slider(om1, r'Time', 0, len(laser.ts())-1, valinit=0, valfmt='%i') #产生第二slider
#     print(len(laser.ts()))
#     def update(val):
#         s1 = int(som1.val)
#         l1.set_xdata(laser.x()[0][s1])
#         l1.set_ydata(laser.y()[0][s1])
#         l2.set_xdata(laser.angle()[0][s1])
#         l2.set_ydata(laser.dist()[0][s1])
#     som1.on_changed(update)
#     plt.show()