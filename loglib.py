import re
import math
from datetime import datetime
import codecs
import chardet
import logging

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
            with open(file,'rb') as f:
                for line in f.readlines(): 
                    try:
                        line = line.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            line = line.decode('gbk')
                        except UnicodeDecodeError:
                            print("Line ",line_num+1, " is skipped due to decoding failure!", " ", line)
                            continue
                    line_num += 1
                    break_flag = False
                    for data in argv:
                        if type(data).__name__ == 'dict':
                            for k in data.keys():
                                if data[k].parse(line):
                                    break_flag = True
                                    break
                            if break_flag:
                                break_flag = False
                                break
                        elif data.parse(line):
                            break


class Data:
    def __init__(self, info):
        self.type = info['type']
        self.regex = re.compile("\[(.*?)\].*\["+self.type+"\]\[(.*?)\]")
        self.short_regx = re.compile("\["+self.type+"\]\[")
        self.info = info['content']
        self.data = dict()
        self.data['t'] = []
        self.parse_error = False
        for tmp in self.info:
            self.data[tmp['name']] =  []
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                values = datas[1].split('|')
                self.data['t'].append(rbktimetodate(datas[0]))
                for tmp in self.info:
                    if 'type' in tmp and 'index' in tmp and 'name' in tmp:
                        if tmp['index'] < len(values):
                            if tmp['type'] == 'double' or tmp['type'] == 'int64':
                                try:
                                    self.data[tmp['name']].append(float(values[int(tmp['index'])]))
                                except:
                                    self.data[tmp['name']].append(0.0)
                            elif tmp['type'] == 'mm':
                                try:
                                    self.data[tmp['name']].append(float(values[int(tmp['index'])])/1000.0)
                                except:
                                    self.data[tmp['name']].append(0.0)
                            elif tmp['type'] == 'cm':
                                try:
                                    self.data[tmp['name']].append(float(values[int(tmp['index'])])/100.0)
                                except:
                                    self.data[tmp['name']].append(0.0)
                            elif tmp['type'] == 'rad':
                                try:
                                    self.data[tmp['name']].append(float(values[int(tmp['index'])])/math.pi * 180.0)
                                except:
                                    self.data[tmp['name']].append(0.0)
                            elif tmp['type'] == 'm':
                                try:
                                    self.data[tmp['name']].append(float(values[int(tmp['index'])]))
                                except:
                                    self.data[tmp['name']].append(0.0)
                            elif tmp['type'] == 'bool':
                                try:
                                    self.data[tmp['name']].append(float(values[int(tmp['index'])] == "true"))
                                except:
                                    self.data[tmp['name']].append(0.0)
                    else:
                        if not self.parse_error:
                            logging.error("Error in {} {} ".format(self.type, tmp.keys()))
                            self.parse_error = True
                return True
            return False
        return False
    def __getitem__(self,k):
        return self.data[k]
    def __setitem__(self,k,value):
        self.data[k] = value

class Laser:
    """  激光雷达的数据
    data[0]: t
    data[1]: ts 激光点的时间戳
    data[2]: angle rad 
    data[3]: dist m
    data[4]: x m
    data[5]: y m
    data[6]: number
    """
    def __init__(self, max_dist):
        """ max_dist 为激光点的最远距离，大于此距离激光点无效"""
        self.regex = re.compile('\[(.*?)\].*\[Laser:? ?(\d*?)\]\[(.*?)\]')
        self.short_regx = re.compile("\[Laser")
        #self.data = [[] for _ in range(7)]
        self.datas = dict()
        self.max_dist = max_dist
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                laser_id = 0
                if datas[1] != "":
                    laser_id =  int(datas[1])
                if laser_id not in self.datas:
                    self.datas[laser_id] = [[] for _ in range(7)]
                self.datas[laser_id][0].append(rbktimetodate(datas[0]))
                tmp_datas = datas[2].split('|')
                self.datas[laser_id][1].append(float(tmp_datas[0]))
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
                self.datas[laser_id][2].append(angle)
                self.datas[laser_id][3].append(dist)
                x , y = polar2xy(angle, dist)
                self.datas[laser_id][4].append(x)
                self.datas[laser_id][5].append(y)
                self.datas[laser_id][6].append(len(x))
                return True
            return False
        return False
    def t(self, laser_index):
        return self.datas[laser_index][0]
    def ts(self, laser_index):
        return self.datas[laser_index][1], self.datas[laser_index][0]
    def angle(self, laser_index):
        return self.datas[laser_index][2], self.datas[laser_index][0]
    def dist(self, laser_index):
        return self.datas[laser_index][3], self.datas[laser_index][0]
    def x(self, laser_index):
        return self.datas[laser_index][4], self.datas[laser_index][0]
    def y(self, laser_index):
        return self.datas[laser_index][5], self.datas[laser_index][0]
    def number(self, laser_index):
        return self.datas[laser_index][6], self.datas[laser_index][0]

class DepthCamera:
    """ 深度摄像头的数据
    data[0]: t
    data[1]: x m
    data[2]: y m
    data[3]: number
    data[4]: ts
    """
    def __init__(self):
        """ max_dist 为激光点的最远距离，大于此距离激光点无效"""
        self.regex = re.compile('\[(.*?)\].* \[DepthCamera\]\[(.*?)\]')
        self.short_regx = re.compile("\[DepthCamera\]\[")
        #self.data = [[] for _ in range(7)]
        self.datas =  [[] for _ in range(5)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                self.datas[0].append(rbktimetodate(datas[0]))
                tmp_datas = datas[1].split('|')
                ts = 0
                if len(tmp_datas)%2 == 0:
                    dx = [float(tmp) for tmp in tmp_datas[0::2]]
                    dy = [float(tmp) for tmp in tmp_datas[1::2]]
                else:
                    dx = [float(tmp) for tmp in tmp_datas[1::2]]
                    dy = [float(tmp) for tmp in tmp_datas[2::2]]
                    ts = float(tmp_datas[0])
                self.datas[1].append(dx)
                self.datas[2].append(dy)
                self.datas[3].append(len(tmp_datas))
                self.datas[4].append(ts)
                return True
            return False
        return False
    def t(self):
        return self.datas[0]
    def x(self):
        return self.datas[1], self.datas[0]
    def y(self):
        return self.datas[2], self.datas[0]
    def number(self):
        return self.datas[3], self.datas[0]
    def ts(self):
        return self.datas[4], self.datas[0]

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
        self.short_regx = re.compile("\[error\]")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:       
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
        self.short_regx = re.compile("\[warning\]")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:              
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
        self.short_regx = re.compile("\[fatal\]")       
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:                   
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
        self.short_regx = re.compile("\[Alarm\]\[Notice\|")
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:              
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
        self.short_regx = re.compile("\[Text\]\[cnt:")
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:                      
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
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
        self.short_regx = re.compile("\[Text\]\[Task finished.")       
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:               
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]

class Service:
    """  服务信息
    data[0]: t
    data[1]: 服务内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Service\].*")
        self.short_regx = re.compile("\[Service\].")          
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:               
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]

class Memory:
    """  内存信息
    t[0]: 
    t[1]:
    t[2]:
    t[3]:
    t[4]:
    t[5]:
    data[0]: used_sys
    data[1]: free_sys
    data[2]: rbk_phy
    data[3]: rbk_vir
    data[4]: rbk_max_phy
    data[5]: rbk_max_vir
    data[6]: cpu_usage
    """
    def __init__(self):
        self.regex = [re.compile("\[(.*?)\].*\[Text\]\[Used system memory *: *(.*?) *[MG]B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Free system memory *: *(.*?) *[MG]B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit physical memory usage *: *(.*?) *[GM]B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit virtual memory usage *: *(.*?) *[GM]B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit Max physical memory usage *: *(.*?) *[GM]B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit Max virtual memory usage *: *(.*?) *[GM]B\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Robokit CPU usage *: *(.*?)%\]")]
        self.short_regx =  re.compile("memory|CPU")
        self.time = [[] for _ in range(7)]
        self.data = [[] for _ in range(7)]
    def parse(self, line):
        short_out = self.short_regx.search(line)
        if short_out:          
            for iter in range(0,7):
                out = self.regex[iter].match(line)
                if out:
                    self.time[iter].append(rbktimetodate(out.group(1)))
                    self.data[iter].append(float(out.group(2)))
                    return True
            return False
        return False
    def t(self):
        return self.time[0]
    def used_sys(self):
        return self.data[0], self.time[0]
    def free_sys(self):
        return self.data[1], self.time[1]
    def rbk_phy(self):
        return self.data[2], self.time[2]
    def rbk_vir(self):
        return self.data[3], self.time[3]
    def rbk_max_phy(self):
        return self.data[4], self.time[4]
    def rbk_max_vir(self):
        return self.data[5], self.time[5]
    def rbk_cpu(self):
        return self.data[6], self.time[6]