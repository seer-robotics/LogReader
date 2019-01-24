from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
import sys
from os import listdir
from os.path import isfile, join, isdir, splitext
from termcolor import colored
from colorama import init
from datetime import datetime

init()
filenames = []
ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_fname = "Report_" + str(ts).replace(':','-').replace(' ','_') + ".txt"
if len(sys.argv) > 1:
    filenames = sys.argv[1:]
    if len(filenames) == 1 and isdir(filenames[0]):
        mypath = filenames[0]
        tmp_files = [join(mypath,f) for f in listdir(mypath) if isfile(join(mypath, f))]
        filenames = []
        for file in tmp_files:
            if splitext(file)[1] == ".log":
                filenames.append(file)
        output_fname = filenames+"\\"+ output_fname
else:
    mypath = "diagnosis\\log"
    tmp_files = [join(mypath,f) for f in listdir(mypath) if isfile(join(mypath, f))]
    filenames = []
    for file in tmp_files:
        if splitext(file)[1] == ".log":
            filenames.append(file)
    output_fname = mypath+"\\"+ output_fname
fid = open(output_fname, "w") 
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
    if len(fat.alarmnum()[0]) >= 1:
        print("FATAL:")
        for iter in range(0, len(fat.alarmnum()[0])):
            print(' '*2, fat.alarmnum()[0][iter]," ",fat.alarminfo()[0][iter])
    if len(err.alarmnum()[0]) >= 1:
        print("ERRORS:")
        for iter in range(0, len(err.alarmnum()[0])):
            print(' '*2,err.alarmnum()[0][iter]," ",err.alarminfo()[0][iter])
    if len(war.alarmnum()[0]) >= 1:
        print("WARNING:")
        for iter in range(0, len(war.alarmnum()[0])):
            print(' '*2,war.alarmnum()[0][iter]," ",war.alarminfo()[0][iter])
    if len(notice.alarmnum()[0]) >= 1:
        print("NOTICE:")
        for iter in range(0, len(notice.alarmnum()[0])):
            print(' '*2,notice.alarmnum()[0][iter]," ",notice.alarminfo()[0][iter])


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
print("Detail information is in the", colored(output_fname,  'yellow', 'on_red', ['bold']), "\nFINISHED!!!")
ch = sys.stdin.read(1)