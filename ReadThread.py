from PyQt5.QtCore import QThread, pyqtSignal
from loglib import MCLoc, IMU, Odometer, Battery, Controller, Send, Get, Laser, Manual 
from loglib import StopPoints, SlowDownPoints, SensorFuser
from loglib import ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, LaserOdometer, TaskStart, TaskFinish
from datetime import timedelta

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

class ReadThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filenames = []
        self.run()

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        self.mcl = MCLoc()
        self.imu = IMU()
        self.odo = Odometer()
        self.battery = Battery()
        self.controller = Controller()
        self.odo = Odometer()
        self.laserOdo = LaserOdometer()
        self.send = Send()
        self.get = Get()
        self.manual = Manual()
        self.stop = StopPoints()
        self.slowdown = SlowDownPoints()
        self.sensorfuser = SensorFuser()
        self.laser = Laser(1000.0)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.taskstart = TaskStart()
        self.taskfinish = TaskFinish()
        self.tlist = []
        if self.filenames:
            log = ReadLog(self.filenames)
            log.parse(self.mcl, self.imu, self.odo, self.battery, self.controller, self.laserOdo, self.stop, self.slowdown, self.sensorfuser,
            self.send, self.get, self.manual, self.laser, self.err, self.war, self.fatal, self.notice, self.taskstart, self.taskfinish)
            #analyze data
            old_imu_flag = decide_old_imu(self.imu.gx()[0], self.imu.gy()[0], self.imu.gz()[0])
            if old_imu_flag:
                self.imu.old2newGyro()
                print('The unit of gx, gy, gz in file is rad/s.')
            else:
                print('The org unit of gx, gy, gz in IMU is LSB/s.')
            tmax = max(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.manual.t() + self.sensorfuser.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            tmin = min(self.mcl.t() + self.odo.t() + self.send.t() + self.get.t() + self.manual.t() + self.sensorfuser.t() + self.laser.t() + self.err.t() + self.fatal.t() + self.notice.t())
            dt = tmax - tmin
            self.tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]
            #save Error
            fid = open("Report.txt", "w") 
            print("="*20, file = fid)
            print("Files: ", self.filenames, file = fid)
            print(len(self.fatal.content()[0]), " FATALs, ", len(self.err.content()[0]), " ERRORs, ", 
                    len(self.war.content()[0]), " WARNINGs, ", len(self.notice.content()[0]), " NOTICEs", file = fid)
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
        self.data = {"mcl.x":self.mcl.x(),"mcl.y":self.mcl.y(),"mcl.theta":self.mcl.theta(), "mcl.confidence":self.mcl.confidence(),
                     "imu.yaw":self.imu.yaw(),"imu.pitch": self.imu.pitch(), "imu.roll": self.imu.roll(), "imu.ts":self.imu.ts(),
                     "imu.ax":self.imu.ax(),"imu.ay":self.imu.ay(),"imu.az":self.imu.az(),
                     "imu.gx":self.imu.gx(),"imu.gy":self.imu.gy(),"imu.gz":self.imu.gz(),
                     "imu.offx":self.imu.offx(),"imu.offy":self.imu.offy(),"imu.offz":self.imu.offz(),
                     "imu.org_gx":([i+j for (i,j) in zip(self.imu.gx()[0],self.imu.offx()[0])], self.imu.gx()[1]),
                     "imu.org_gy":([i+j for (i,j) in zip(self.imu.gy()[0],self.imu.offy()[0])], self.imu.gy()[1]),
                     "imu.org_gz":([i+j for (i,j) in zip(self.imu.gz()[0],self.imu.offz()[0])], self.imu.gz()[1]),
                     "odo.ts": self.odo.ts(),"odo.x":self.odo.x(),"odo.y":self.odo.y(),"odo.theta":self.odo.theta(),"odo.stop":self.odo.stop(),
                     "odo.vx":self.odo.vx(),"odo.vy":self.odo.vy(),"odo.vw":self.odo.vw(),"odo.steer_angle":self.odo.steer_angle(),
                     "odo.encode0":self.odo.encode0(),"odo.encode1":self.odo.encode1(),"odo.encode2":self.odo.encode2(),"odo.encode3":self.odo.encode3(),
                     "laserOdo.ts":self.laserOdo.ts(),"laserOdo.x":self.laserOdo.x(),"laserOdo.y":self.laserOdo.y(),"laserOdo.angle":self.laserOdo.angle(),
                     "laser.ts":self.laser.ts(),
                     "sensorfuser.local":self.sensorfuser.localnum(),"sensorfuser.global":self.sensorfuser.globalnum(),
                     "stop.x":self.stop.x(),"stop.y":self.stop.y(),"stop.type":self.stop.type(), "stop.id":self.stop.id(), "stop.dist": self.stop.dist(),
                     "slowdown.x":self.slowdown.x(),"slowdown.y":self.slowdown.y(),"slowdown.type":self.slowdown.type(), "slowdown.id":self.slowdown.id(), "slowdown.dist": self.slowdown.dist(),
                     "send.vx":self.send.vx(),"send.vy":self.send.vy(),"send.vw":self.send.vw(),"send.steer_angle":self.send.steer_angle(),
                     "send.max_vx":self.send.max_vx(),"send.max_vw":self.send.max_vw(),
                     "manual.vx": self.manual.vx(), "manual.vy": self.manual.vy(), "manual.vw":self.manual.vw(), "manual.steer_angle": self.manual.steer_angle(),
                     "get.vx":self.get.vx(),"get.vy":self.get.vy(),"get.vw":self.get.vw(), "get.steer_angle":self.get.steer_angle(),
                     "get.max_vx":self.get.max_vx(),"get.max_vw":self.get.max_vw(),
                     "battery.percentage": self.battery.percentage(), "battery.current": self.battery.current(), "battery.voltage": self.battery.voltage(),
                     "battery.ischarging": self.battery.ischarging(), "battery.temperature": self.battery.temperature(), "battery.cycle": self.battery.cycle(),
                     "controller.temp": self.controller.temp(), "controller.humi": self.controller.humi(), "controller.voltage":self.controller.voltage(),
                     "controller.emc": self.controller.emc(),"controller.brake":self.controller.brake(),"controller.driveremc":self.controller.driveremc(),
                     "controller.manualcharge": self.controller.manualcharge(),"controller.autocharge": self.controller.autocharge(), "controller.electric": self.controller.electric()}
        self.signal.emit(self.filenames)