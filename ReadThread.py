from PyQt5.QtCore import QThread, pyqtSignal
from loglib import Data, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, TaskStart, TaskFinish, Service
from loglib import Memory, DepthCamera
from datetime import timedelta
from datetime import datetime
import os
import json as js
import logging
import math
import time

def decide_old_imu(gx,gy,gz):
    for v in gx:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gy:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gz:
        if abs(round(v) - v) > 1e-5:
            return True
    return False

def rad2LSB(data):
    new_data = [v/math.pi*180.0*16.4 for v in data]
    return new_data

def Fdir2Flink(f):
    flink = " <a href='file:///" + f + "'>"+f+"</a>"
    return flink

class ReadThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filenames = []
        self.log_config = "log_config.json"
        self.js = dict()
        self.content = dict()
        self.data = dict()
        self.log =  []
        self.tlist = []
        try:
            f = open('log_config.json')
            self.js = js.load(f)
        except FileNotFoundError:
            logging.error('Failed to open log_config.json')
            self.log.append('Failed to open log_config.json')

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        try:
            f = open(self.log_config)
            self.js = js.load(f)
            f.close()
            logging.error("Load {}".format(self.log_config))
            self.log.append("Load {}".format(self.log_config))
        except FileNotFoundError:
            logging.error("Failed to open {}".format(self.log_config))
            self.log.append("Failed to open {}".format(self.log_config))
        self.content = dict()
        for k in list(self.js):
            self.content[k] = Data(self.js[k]) 
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.taskstart = TaskStart()
        self.taskfinish = TaskFinish()
        self.service = Service()
        self.memory = Memory()
        self.depthcamera = DepthCamera()
        self.tlist = []
        self.log =  []
        if self.filenames:
            log = ReadLog(self.filenames)
            time_start=time.time()
            log.parse(self.content, self.laser, self.err, self.war, self.fatal, self.notice, self.taskstart, self.taskfinish, self.service, self.memory, self.depthcamera)
            time_end=time.time()
            self.log.append('read time cost: ' + str(time_end-time_start))
            #analyze content
            old_imu_flag = False
            if 'IMU' in self.js:
                old_imu_flag = decide_old_imu(self.content['IMU']['gx'], self.content['IMU']['gy'], self.content['IMU']['gz'])
            if old_imu_flag:
                self.content['IMU']['gx'] = rad2LSB(self.content['IMU']['gx'])
                self.content['IMU']['gy'] = rad2LSB(self.content['IMU']['gy'])
                self.content['IMU']['gz'] = rad2LSB(self.content['IMU']['gz'])
                logging.info('The unit of gx, gy, gz in file is rad/s.')
                self.log.append('The unit of gx, gy, gz in file is rad/s.') 
            else:
                logging.info('The org unit of gx, gy, gz in IMU is LSB/s.')
                self.log.append('The org unit of gx, gy, gz in IMU is LSB/s.')
            # tmax = max(self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t())
            # tmin = min(self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t())
            tmax = datetime.fromtimestamp(100000000) 
            tmin = datetime.now()
            init_t = True
            for k in self.content.keys():
                if init_t:
                    if len(self.content[k]['t']) > 0:
                        tmax = max(self.content[k]['t'])
                        tmin = min(self.content[k]['t'])
                        init_t = False
                else:
                    tmax = max([tmax] + self.content[k]['t'])
                    tmin = min([tmin] + self.content[k]['t'])
            dt = tmax - tmin
            self.tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]
            #save Error
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_fname = "Report_" + str(ts).replace(':','-').replace(' ','_') + ".txt"
            path = os.path.dirname(self.filenames[0])
            output_fname = path + "/" + output_fname
            self.log.append("Report File:" + Fdir2Flink(output_fname))
            fid = open(output_fname,"w") 
            print("="*20, file = fid)
            print("Files: ", self.filenames, file = fid)
            print(len(self.fatal.content()[0]), " FATALs, ", len(self.err.content()[0]), " ERRORs, ", 
                    len(self.war.content()[0]), " WARNINGs, ", len(self.notice.content()[0]), " NOTICEs", file = fid)
            self.log.append(str(len(self.fatal.content()[0])) + " FATALs, " + str(len(self.err.content()[0])) + 
                " ERRORs, " + str(len(self.war.content()[0])) + " WARNINGs, " + str(len(self.notice.content()[0])) + " NOTICEs")
            print("FATALs:", file = fid)
            for data in self.fatal.content()[0]:
                print(data, file = fid)
            print("ERRORs:", file = fid)
            for data in self.err.content()[0]:
                print(data,file = fid)
            print("WARNINGs:", file = fid)
            for data in self.war.content()[0]:
                print(data, file = fid)
            print("NOTICEs:", file = fid)
            for data in self.notice.content()[0]:
                print(data, file = fid)
            fid.close()
        #creat dic
        self.data = {"memory.used_sys":self.memory.used_sys(), "memory.free_sys":self.memory.free_sys(), "memory.rbk_phy": self.memory.rbk_phy(),
                     "memory.rbk_vir":self.memory.rbk_vir(),"memory.rbk_max_phy":self.memory.rbk_max_phy(),"memory.rbk_max_vir":self.memory.rbk_max_vir(),
                     "memory.cpu":self.memory.rbk_cpu()}
        for k in self.content.keys():
            for name in self.content[k].data.keys():
                if name != 't':
                    self.data[k+'.'+name] = (self.content[k][name], self.content[k]['t'])
        if 'IMU' in self.js:
            self.data["IMU.org_gx"] = ([i+j for (i,j) in zip(self.content['IMU']['gx'],self.content['IMU']['offx'])], self.content['IMU']['t'])
            self.data["IMU.org_gy"] = ([i+j for (i,j) in zip(self.content['IMU']['gy'],self.content['IMU']['offy'])], self.content['IMU']['t'])
            self.data["IMU.org_gz"] = ([i+j for (i,j) in zip(self.content['IMU']['gz'],self.content['IMU']['offz'])], self.content['IMU']['t'])
        for k in self.laser.datas.keys():
            self.data["laser"+str(k)+'.'+"ts"] = self.laser.ts(k)
            self.data["laser"+str(k)+'.'+"number"] = self.laser.number(k)
        self.data["depthcamera.number"] = self.depthcamera.number()
        self.data["depthcamera.ts"] = self.depthcamera.ts()
        self.signal.emit(self.filenames)