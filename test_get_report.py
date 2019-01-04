from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
import sys
from os import listdir
from os.path import isfile, join
from termcolor import colored
from colorama import init
init()

filenames = []
if len(sys.argv) > 1:
    filenames = sys.argv[1:]
else:
    mypath = "diagnosis\\log"
    filenames = [join(mypath,f) for f in listdir(mypath) if isfile(join(mypath, f))]
fid = open("Report.txt", "w", encoding='utf-8') 
for filename in filenames:
    log = ReadLog([filename])
    err = ErrorLine()
    war = WarningLine()
    fat = FatalLine()
    notice = NoticeLine()
    log.parse(err, war, fat, notice)
    print("="*20)
    if len(err.content()[0]) >= 1 or len(fat.content()[0]) >= 1 :
        print(colored("Files: "+ filename,  'red', None, ['bold']))
    elif len(war.content()[0]) >=1:
        print(colored("Files: " + filename, 'yellow', None, ['bold']))
    else:
        print("Files: ", filename)
    print( len(fat.content()[0]), " FATALs, ", len(err.content()[0]), " ERRORs, ", len(war.content()[0]), " WARNINGs, ", len(notice.content()[0]), " NOTICEs")

    print("="*20, file = fid)
    print("Files: ", filename, file = fid)
    print(len(fat.content()[0]), " FATALs, ", len(err.content()[0]), " ERRORs, ", len(war.content()[0]), " WARNINGs, ", len(notice.content()[0]), " NOTICEs", file = fid)
    print("FATALs:", file = fid)
    for data in fat.content()[0]:
        print(data, file = fid)
    print("ERRORs:", file = fid)
    for data in err.content()[0]:
        print(data,file = fid)
    print("WARNINGs:", file = fid)
    for data in war.content()[0]:
        print(data, file = fid)
    print("NOTICEs:", file = fid)
    for data in notice.content()[0]:
        print(data, file = fid)
fid.close()
print("FINISHED!!!")
ch = sys.stdin.read(1)