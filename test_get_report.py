from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider,RadioButtons
import sys
mcl = MCLoc()
imu = IMU()
odo = Odometer()
send = Send()
get = Get()
laser = Laser(1000.0)
err = ErrorLine()
war = WarningLine()
fat = FatalLine()
notice = NoticeLine()
log = ReadLog(sys.argv[1:])
log.parse(mcl, imu, odo, send, get, laser, err, war, fat, notice)

f = open("Report.txt", "w", encoding='utf-8') 
print("Files: ", sys.argv[1:], file = f)
print(len(err.content()[0]), " ERRORs, ", len(war.content()[0]), " WARNINGs, ", len(fat.content()[0]), " FATALs, ", len(notice.content()[0]), " NOTICEs", file = f)
print("ERRORs:", file = f)
for data in err.content()[0]:
    print(data,file = f)
print("WARNINGs:", file = f)
for data in war.content()[0]:
    print(data, file = f)
print("FATALs:", file = f)
for data in fat.content()[0]:
    print(data, file = f)
print("NOTICEs:", file = f)
for data in notice.content()[0]:
    print(data, file = f)
f.close()