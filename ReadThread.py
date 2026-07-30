from PyQt5.QtCore import QThread, pyqtSignal
from loglibPlus import Data, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, TaskStart, TaskFinish, Service, ParticleState
from loglibPlus import Memory, DepthCamera, RobotStatus, obsDetect
from logconfig import append_log_config_entries
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
        self.data_org_key = dict() # 用于动态解析日志文件
        self.name2orgKey = dict() # 用于动态解析日志文件
        self.ylabel = dict()
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
        self.obsDetect = obsDetect()
        self.particle = ParticleState()
        self.rstatus = RobotStatus()
        self.log =  []
        self.tlist = []
        self.output_fname = ""
        self.cpu_num = 4
        self.reader = None
        try:
            with open(self.log_config, encoding='UTF-8') as f:
                self.js = js.load(f)
        except FileNotFoundError:
            logging.error('Failed to open log_config.json')
            self.log.append('Failed to open log_config.json')

    @staticmethod
    def _create_config_parsers(entry):
        """Create the Data objects represented by one config entry."""
        rule_type = entry['type']
        if isinstance(rule_type, list):
            return {
                item: Data(entry, item)
                for item in rule_type
            }
        if rule_type == 'Text':
            text_key = entry.get('textKey')
            return {text_key: Data(entry, rule_type, text_key)}
        path_flag = entry['content'] == 'path'
        return {rule_type: Data(entry, rule_type, None, path_flag)}

    @staticmethod
    def _content_series(content_key, parser):
        real_key = content_key
        array_data_name = None
        if 'name' in parser.data and parser.data['name']:
            array_data_name = parser.data['name'][0]
            real_key = content_key[:-1] + '.' + array_data_name

        series = []
        for field_name in parser.data:
            if field_name == 't':
                continue
            data_key = real_key + '.' + field_name
            description = parser.description[field_name]
            if array_data_name is not None:
                ylabel = array_data_name + '.' + description
            else:
                ylabel = description
                if (isinstance(description, str) and description
                        and description in data_key):
                    ylabel = data_key
            series.append((data_key, field_name, ylabel))
        return real_key, series

    def _register_content_data(self, content_keys):
        for content_key in content_keys:
            parser = self.content[content_key]
            real_key, series = self._content_series(content_key, parser)
            self.name2orgKey[real_key] = content_key
            for data_key, field_name, ylabel in series:
                self.data[data_key] = (
                    parser[field_name], parser['t'])
                self.ylabel[data_key] = ylabel
                self.data_org_key[data_key] = content_key

    def add_log_configs(self, entries, config_path=None):
        """Persist and register new parsing rules against loaded log lines."""
        if self.isRunning():
            raise RuntimeError('日志仍在加载，暂时不能添加解释规则')
        if self.reader is None:
            raise RuntimeError('请先加载日志，再添加解释规则')

        new_parsers = {}
        for entry in entries.values():
            for content_key, parser in self._create_config_parsers(entry).items():
                if content_key in self.content or content_key in new_parsers:
                    raise ValueError(
                        '日志类型已存在：{}'.format(content_key))
                new_parsers[content_key] = parser

        # Parse before persistence so malformed runtime rules leave the file
        # and the active data dictionaries untouched.
        for parser in new_parsers.values():
            parser.parse_now(self.reader.lines)

        new_series = []
        for content_key, parser in new_parsers.items():
            _real_key, series = self._content_series(content_key, parser)
            for data_key, _field_name, _ylabel in series:
                if data_key in self.data or data_key in new_series:
                    raise ValueError(
                        '曲线数据名称已存在：{}'.format(data_key))
                new_series.append(data_key)

        target_path = config_path or self.log_config
        append_log_config_entries(target_path, entries)
        self.js.update(entries)
        self.content.update(new_parsers)
        self._register_content_data(new_parsers.keys())
        self.log.append(
            'Added log config: {}'.format(', '.join(entries.keys())))
        return new_series

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        try:
            with open(self.log_config,encoding= 'UTF-8') as f:
                self.js = js.load(f)
                logging.info("Load {}".format(self.log_config))
                self.log.append("Load {}".format(self.log_config))
        except FileNotFoundError:
            logging.error("Failed to open {}".format(self.log_config))
            self.log.append("Failed to open {}".format(self.log_config))
        self.content = dict()
        content_delay = dict()
        for k in self.js:
            if "type" in self.js[k] and "content" in self.js[k]:
                if k == "LocationEachFrame" or \
                k == "StopPoints"  or \
                k == "SlowDownPoints" or \
                k == "MotorInfo" or \
                (isinstance(self.js[k]['content'], str) and self.js[k]["content"] == "key|value") or \
                (isinstance(self.js[k]['content'], str) and self.js[k]['content'] == "path"):
                    print("type", self.js[k]["type"])
                    if isinstance(self.js[k]['content'], str) and self.js[k]['content'] == "path":
                        self.content[self.js[k]["type"]] = Data(self.js[k], self.js[k]["type"], None, True)
                    if isinstance(self.js[k]['type'], list):
                        for type in self.js[k]["type"]:
                            self.content[type] = Data(self.js[k], type)
                    else:
                        self.content[self.js[k]["type"]] = Data(self.js[k], self.js[k]["type"])
                else:
                    if isinstance(self.js[k]['type'], list):
                        for type in self.js[k]["type"]:
                            content_delay[type] = Data(self.js[k], type)
                    elif isinstance(self.js[k]['type'], str):
                        if self.js[k]['type'] == "Text" and isinstance(self.js[k].get("textKey", None), str):
                            content_delay[self.js[k]['textKey']] = Data(self.js[k], self.js[k]['type'], self.js[k]['textKey'])
                        else:
                            if isinstance(self.js[k]['content'], str) and self.js[k]['content'] == "path":
                                content_delay[self.js[k]['type']] = Data(self.js[k], self.js[k]['type'], None, True)
                            else:
                                content_delay[self.js[k]['type']] = Data(self.js[k], self.js[k]['type'], None)
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.taskstart = TaskStart()
        self.taskfinish = TaskFinish()
        self.service = Service()
        self.memory = Memory()
        self.depthcamera = DepthCamera()
        self.obsDetect : obsDetect = obsDetect()
        self.particle = ParticleState()
        self.rstatus = RobotStatus()
        self.tlist = []
        self.log =  []
        self.output_fname = ""
        if self.filenames:
            if self.reader == None:
                self.reader = ReadLog(self.filenames)
            else:
                self.reader.filenames = self.filenames
            self.reader.thread_num = self.cpu_num
            time_start=time.time()
            self.reader.parse(self.content, self.laser, self.err, 
                            self.war, self.fatal, self.notice, 
                            self.taskstart, self.taskfinish, self.service, 
                            self.memory, self.depthcamera, self.particle,
                            self.rstatus, self.obsDetect)
            time_end=time.time()
            self.log.append('read time cost: ' + str(time_end-time_start))
            self.content.update(content_delay)
            #analyze content
            # old_imu_flag = False
            # if 'IMU' in self.js:
            #     old_imu_flag = decide_old_imu(self.content['IMU']['gx'], self.content['IMU']['gy'], self.content['IMU']['gz'])
            # if old_imu_flag:
            #     self.content['IMU']['gx'] = rad2LSB(self.content['IMU']['gx'])
            #     self.content['IMU']['gy'] = rad2LSB(self.content['IMU']['gy'])
            #     self.content['IMU']['gz'] = rad2LSB(self.content['IMU']['gz'])
            #     logging.info('The unit of gx, gy, gz in file is rad/s.')
            #     self.log.append('The unit of gx, gy, gz in file is rad/s.') 
            # else:
            #     logging.info('The org unit of gx, gy, gz in IMU is LSB/s.')
            #     self.log.append('The org unit of gx, gy, gz in IMU is LSB/s.')
            tmp_tlist = self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t()
            tmax, tmin = None, None
            if len(tmp_tlist) > 0:
                tmax = max(self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t())
                tmin = min(self.err.t() + self.fatal.t() + self.notice.t() + self.memory.t() + self.service.t())
            if tmax != None:
                tmax = max(tmax, self.reader.tmax)
            else:
                tmax = self.reader.tmax
            if tmin != None:
                tmin = min(tmin, self.reader.tmin)
            else:
                tmin = self.reader.tmin
            dt = tmax - tmin
            self.tlist = [tmin, tmax]
            self.log.append(
                '{} FATALs, {} ERRORs, {} WARNINGs, {} NOTICEs, '
                '{} TASK STARTs, {} TASK FINISHes, {} SERVICEs'.format(
                    len(self.fatal.content()[0]),
                    len(self.err.content()[0]),
                    len(self.war.content()[0]),
                    len(self.notice.content()[0]),
                    len(self.taskstart.content()[0]),
                    len(self.taskfinish.content()[0]),
                    len(self.service.content()[0])))
        # create curve data dictionaries
        self._register_content_data(self.content.keys())
        if 'IMU' in self.js:
            self.data["IMU.org_gx"] = ([i+j for (i,j) in zip(self.content['IMU']['gx'],self.content['IMU']['offx'])], self.content['IMU']['t'])
            self.data["IMU.org_gy"] = ([i+j for (i,j) in zip(self.content['IMU']['gy'],self.content['IMU']['offy'])], self.content['IMU']['t'])
            self.data["IMU.org_gz"] = ([i+j for (i,j) in zip(self.content['IMU']['gz'],self.content['IMU']['offz'])], self.content['IMU']['t'])
            self.ylabel["IMU.org_gx"] = "原始的gx degree/s"
            self.ylabel["IMU.org_gy"] = "原始的gy degree/s"
            self.ylabel["IMU.org_gz"] = "原始的gz degree/s"
            self.data_org_key["IMU.org_gx"] = "IMU"
            self.data_org_key["IMU.org_gy"] = "IMU"
            self.data_org_key["IMU.org_gz"] = "IMU"

        self.data.update({"memory.used_sys":self.memory.used_sys(), "memory.free_sys":self.memory.free_sys(), "memory.rbk_phy": self.memory.rbk_phy(),
                    "memory.rbk_vir":self.memory.rbk_vir(),"memory.rbk_max_phy":self.memory.rbk_max_phy(),"memory.rbk_max_vir":self.memory.rbk_max_vir(),
                    "memory.cpu":self.memory.rbk_cpu(),"memory.sys_cpu":self.memory.sys_cpu()})
        self.ylabel.update({"memory.used_sys": "used_sys MB", "memory.free_sys":"free_sys MB", "memory.rbk_phy": "rbk_phy MB",
                    "memory.rbk_vir":"rbk_vir MB","memory.rbk_max_phy":"rbk_max_phy MB","memory.rbk_max_vir":"rbk_max_vir MB",
                    "memory.cpu":"cpu %", "memory.sys_cpu":"sys_cpu %"})

        for k in self.laser.datas.keys():
            self.data["laser"+str(k)+'.'+"ts"] = self.laser.ts(k)
            self.data["laser"+str(k)+'.'+"number"] = self.laser.number(k)
            self.ylabel["laser"+str(k)+'.'+"ts"] = "激光的时间戳"
            self.ylabel["laser"+str(k)+'.'+"number"] = "激光的id"

        self.data["depthcamera.number"] = self.depthcamera.number()
        self.data["depthcamera.ts"] = self.depthcamera.ts()
        self.ylabel["depthcamera.number"] = "深度摄像头id"
        self.ylabel["depthcamera.ts"] = "深度摄像头时间戳"
        
        self.data["obsDetect.number"] = self.obsDetect.number()
        self.data["obsDetect.ts"] = self.obsDetect.ts()
        self.data["obsDetect.name"] = self.obsDetect.device_name()
        self.ylabel["obsDetect.number"] = "感知Sensor id"
        self.ylabel["obsDetect.ts"] = "感知Sensor 时间戳"
        self.ylabel["obsDetect.name"] = "感知Sensor 名称"

        self.data["particle.number"] = self.particle.number()
        self.data["particle.ts"] = self.particle.ts()
        self.ylabel["particle.number"] = "粒子数目"
        self.ylabel["particle.ts"] = "粒子时间戳"

        self.signal.emit(self.filenames)

    def getData(self, vkey):
        if vkey in self.data:
            if not self.data[vkey][0]:
                if vkey in self.data_org_key:
                    org_key = self.data_org_key[vkey]
                    if not self.content[org_key].parsed_flag:
                        # time_start=time.time()
                        self.content[org_key].parse_now(self.reader.lines)
                        for name in self.content[org_key].data.keys():
                            if name != 't':
                                self.ylabel[org_key+'.'+name] = self.content[org_key].description[name]                    
                        # time_end=time.time()
                        # print('real read time cost: ' + str(time_end-time_start))
                    name = vkey.rsplit('.', 1)[-1]
                    if org_key == "IMU" and "org" in name:
                        if len(name) == 6:
                            g = name[4::]  #org_gx, org_gy, org_gz
                            off = "off" + name[-1] #offx, offy, offz
                            self.data[vkey] = (
                                [i + j for (i, j) in zip(
                                    self.content[org_key][g],
                                    self.content[org_key][off])],
                                self.content[org_key]['t'])
                        else:
                            self.data[vkey] = ([], [])              
                    else:
                        self.data[vkey] = (self.content[org_key][name], self.content[org_key]['t'])
            return self.data[vkey]
        else:
            return [[],[]]

    def getReportFileAddr(self):
        """Backward-compatible API; reports are now kept in memory."""
        return self.output_fname


