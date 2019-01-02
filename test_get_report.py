from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
import sys
from os import listdir
from os.path import isfile, join
filenames = []
if len(sys.argv) > 1:
    filenames = sys.argv[1:]
else:
    mypath = "diagnosis\\log"
    filenames = [join(mypath,f) for f in listdir(mypath) if isfile(join(mypath, f))]
fid = open("Report.txt", "w", encoding='utf-8') 
out = sys.stdout
outlists = [fid,out]
for filename in filenames:
    log = ReadLog([filename])
    err = ErrorLine()
    war = WarningLine()
    fat = FatalLine()
    notice = NoticeLine()
    log.parse(err, war, fat, notice)
    for f in outlists:
        print("="*20, file = f)
        print("Files: ", filename, file = f)
        print(len(err.content()[0]), " ERRORs, ", len(war.content()[0]), " WARNINGs, ", len(fat.content()[0]), " FATALs, ", len(notice.content()[0]), " NOTICEs", file = f)
    print("ERRORs:", file = fid)
    for data in err.content()[0]:
        print(data,file = fid)
    print("WARNINGs:", file = fid)
    for data in war.content()[0]:
        print(data, file = fid)
    print("FATALs:", file = fid)
    for data in fat.content()[0]:
        print(data, file = fid)
    print("NOTICEs:", file = fid)
    for data in notice.content()[0]:
        print(data, file = fid)
fid.close()
print("FINISHED!!!")
ch = sys.stdin.read(1)