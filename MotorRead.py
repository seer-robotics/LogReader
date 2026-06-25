import json, gzip, re
from os import close, name
try:
    from loglibPlus import open_log_file as _open_log_file
except Exception:
    _open_log_file = None


def _open_motor_log(file_name):
    """打开 motor 日志文件,支持 .log/.gz/.zst"""
    if file_name.endswith(".log"):
        return open(file_name, 'rb')
    if file_name.endswith(".zst") and _open_log_file is not None:
        # _ZstdLogReader 是上下文管理器,这里需要返回类文件对象
        return _open_log_file(file_name, 'rb').__enter__()
    return gzip.open(file_name, 'rb')

def getMotorFromModel(model_path):
    path = model_path
    file = open(path, "rb")
    fileJson = json.load(file)
    crop_cells = fileJson["model"]
    device_types = fileJson["deviceTypes"]
    for type in device_types:
        if type["name"] == "motor":
            devices = type["devices"]
            # print(devices)
            file.close()
            return devices
    

def getMotorNameTypeDict(model_path):
    name_type_dict = {}
    for device in getMotorFromModel(model_path):
        motor_name = device["name"]
        device_params = device["deviceParams"]
        for param in device_params:
            if param["key"] == "func":
                motor_type = param["comboParam"]["childKey"]
                name_type_dict[motor_name] = motor_type
                # print("name %s: %s" % (motor_name, motor_type))
    return name_type_dict

def getMotorNameBrandDict(model_path):
    name_brand_dict = {}
    for device in getMotorFromModel(model_path):
        motor_name = device["name"]
        device_params = device["deviceParams"]
        for param in device_params:
            if param["key"] == "brand":
                motor_brand = param["comboParam"]["childKey"]
                name_brand_dict[motor_name] = motor_brand
                # print("name %s: %s" % (motor_name, motor_type))
    return name_brand_dict

def getMotorNames(model_path):
    name_list = []
    for device in getMotorFromModel(model_path):
        motor_name = device["name"]
        name_list.append(motor_name)
    return name_list

def getNameMotorInfoDict(file_name, motor_name_list):
    name_motorinfo = {}
    try:
        file = _open_motor_log(file_name)
    except Exception:
        print("fail")
        return name_motorinfo
    
    match_dict = {}
    for i in motor_name_list:
        match_dict[i] = False

    for line in file.readlines(): 
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            try:
                line = line.decode('gbk')
            except UnicodeDecodeError:
                continue
        regex = re.compile("\[(.*?)\].*\[(.*?)\]\[(.*?)\]")
        out = regex.match(line)
        if out:
            if ("MotorInfo" in out.group(2)) and (not "MotorInfoISO" in out.group(2)):
                motor_name = out.group(3).split("|")[10]
                match_dict[motor_name] = True
                name_motorinfo[motor_name] = out.group(2)
        all_match = True
        for key in match_dict:
            all_match = all_match and match_dict[key]
        
        if not all_match:
            continue
        else:
            break
    # print(name_motorinfo)
    file.close()
    return name_motorinfo;

def getNameMotorCmdDict(file_name, motor_name_list):
    name_motorcmd = {}
    try:
        file = _open_motor_log(file_name)
    except Exception:
        print("fail")
        return name_motorcmd
    
    match_dict = {}
    for i in motor_name_list:
        match_dict[i] = False

    for line in file.readlines(): 
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            try:
                line = line.decode('gbk')
            except UnicodeDecodeError:
                continue
        regex = re.compile("\[(.*?)\].*\["+"MotorCmd"+"\]\[(.*?)\]")
        out = regex.match(line)
        if out:
            data = out.group(2).split("|")
            for index, d in enumerate(range(0, len(data), 2)):
                match_dict[data[d]] = True
                name_motorcmd[data[d]] = "motor" + str(index)
        all_match = True
        for key in match_dict:
            all_match = all_match and match_dict[key]
        
        if not all_match:
            continue
        else:
            break
    # print(name_motorcmd)
    file.close()
    return name_motorcmd;
            

if __name__ == "__main__":
    print(getMotorNames("robot.model"))
    print(getMotorNameTypeDict("robot.model"))
    getNameMotorInfoDict("222.log", getMotorNames("robot.model"))
    getNameMotorCmdDict("222.log", getMotorNames("robot.model"))