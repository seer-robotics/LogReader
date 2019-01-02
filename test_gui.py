from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine
from loglib import findrange
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider,Button, TextBox
import sys
from datetime import datetime, timedelta

mcl = MCLoc()
imu = IMU()
odo = Odometer()
send = Send()
get = Get()
laser = Laser(1000.0)
err = ErrorLine()
war = WarningLine()
fatal = FatalLine()
notice = NoticeLine()
log = ReadLog(sys.argv[1:])
log.parse(mcl, imu, odo, send, get, laser, err, war,fatal, notice)

tmax = max(mcl.t() + odo.t() + send.t() + get.t() + laser.t() + err.t() + fatal.t() + notice.t())
tmin = min(mcl.t() + odo.t() + send.t() + get.t() + laser.t() + err.t() + fatal.t() + notice.t())
dt = tmax - tmin
tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]

f = open("Report.txt", "w", encoding='utf-8') 
print(len(fatal.content()[0]), "FATALs", len(err.content()[0]), " ERRORs, ", len(war.content()[0]), " WARNINGs", len(notice.content()[0]), "NOTICEs", file = f )
print("FATALs:", file = f)
for data in fatal.content()[0]:
    print(data,file = f)
print("ERRORs:", file = f)
for data in err.content()[0]:
    print(data,file = f)
print("WARNINGs:", file = f)
for data in war.content()[0]:
    print(data, file = f)
print("NOTICEs:", file = f)
for data in notice.content()[0]:
    print(data, file = f)
f.close()

def drawFEWN(ax):
    """ 绘制 Fatal, Error, Warning在坐标轴上"""
    fl, el, wl,nl = None, None, None, None
    for tmp in fatal.t():
        fl, = ax.plot((tmp,tmp),[-1e10, 1e10],'k-')
    for tmp in err.t():
        el, = ax.plot((tmp,tmp),[-1e10, 1e10],'r-.')
    for tmp in war.t():
        wl, = ax.plot((tmp,tmp),[-1e10, 1e10],'y--')
    for tmp in notice.t():
        nl, = ax.plot((tmp,tmp),[-1e10, 1e10],'g:')
    ax.legend((fl, el, wl, nl), ('fatal', 'error', 'warning', 'notice'), loc='upper right')


if len(mcl.t()) > 0:
    fig = plt.figure(1)
    ax2 = plt.axes([0.1, 0.2, 0.8, 0.3])
    #画图 mcl.t, mcl.x
    drawFEWN(ax2)
    l2, = ax2.plot(mcl.y()[1], mcl.y()[0], '.')
    max_range = max(mcl.y()[0]) - min(mcl.y()[0])
    ax2.set_ylim(min(mcl.y()[0]) - 0.05 * max_range, max(mcl.y()[0]) + 0.05 * max_range)
    ax2.set_xlabel("t")
    ax2.grid()
    #画图 mcl.t, mcl.x
    ax1 = plt.axes([0.1, 0.58, 0.8, 0.3])
    drawFEWN(ax1)
    l1, = ax1.plot(mcl.x()[1], mcl.x()[0], '.')
    max_range = max(mcl.x()[0]) - min(mcl.x()[0])
    ax1.set_ylim(min(mcl.x()[0]) - 0.05 * max_range, max(mcl.x()[0]) + 0.05 * max_range)
    ax1.set_xticklabels("")
    ax1.grid()

    #slider
    axcolor = 'lightgoldenrodyellow'  # slider的颜色
    om1= plt.axes([0.1, 0.1, 0.8, 0.05], facecolor=axcolor) # 第一slider的位置
    som1 = Slider(om1, r'Start',0, len(tlist)-1, valinit=0) #产生第一slider
    # slider的val text 重写
    som1.valtext.set_text("")
    som1.valtext = om1.text(0.02, 0.5, mcl.t()[0].strftime("%H:%M:%S.%f"),
                        transform=om1.transAxes,
                        verticalalignment='center',
                        horizontalalignment='left')
    som1.valtext.set_text(mcl.t()[0].strftime("%H:%M:%S.%f"))
    om2= plt.axes([0.1, 0.02, 0.8, 0.05], facecolor=axcolor) # 第一slider的位置
    som2 = Slider(om2, r'End', 1, len(tlist)-1, valinit=len(tlist)-1) #产生第一slider
    # slider的val text 重写
    som2.valtext.set_text("")
    som2.valtext = om2.text(0.02, 0.5, mcl.t()[-1].strftime("%H:%M:%S.%f"),
                        transform=om2.transAxes,
                        verticalalignment='center',
                        horizontalalignment='left')
    # Text input
    box1 = plt.axes([0.1, 0.9, 0.8, 0.04])
    text_box1 = TextBox(box1, 'Evaluate', initial="mcl.x")
    ax1.set_ylabel("mcl.x")
    box2 = plt.axes([0.1, 0.52, 0.8, 0.04])
    text_box2 = TextBox(box2, 'Evaluate', initial="mcl.y")
    ax2.set_ylabel("mcl.y")
    class Update:
        def __init__(self, t, t1, data1, t2, data2):
            self.t = t
            self.inds = 0
            self.inde = len(t)-1 
            self.ts = t[0]
            self.te = t[-1]

            self.t1 = t1
            self.data1 = data1
            self.t2 = t2
            self.data2 = data2
        def slider_start(self, event):
            self.inds = int(som1.val)
            if self.inds >= self.inde :
                self.inds = self.inde - 1
                som1.set_val(self.inds)
            self.ts = self.t[self.inds]
            som1.valtext.set_text(self.ts.strftime("%H:%M:%S.%f"))
            ax1.set_xlim(self.ts, self.te)
            ax2.set_xlim(self.ts, self.te)
            plt.draw()
        def slider_end(self, event):
            self.inde = int(som2.val)
            if self.inds >= self.inde :
                self.inde = self.inds + 1
                som2.set_val(self.inde)
            self.te = self.t[self.inde]
            som2.valtext.set_text(self.te.strftime("%H:%M:%S.%f"))
            ax1.set_xlim(self.ts, self.te)
            ax2.set_xlim(self.ts, self.te)
            plt.draw()
        def submit1(self, event):
            val = event.replace(' ',"")
            self.data1, self.t1 = eval(val+"()")
            ax1.set_ylabel(val)
            self.reset_data1()
        def submit2(self, event):
            val = event.replace(' ',"")
            self.data2, self.t2 = eval(val+"()")
            ax2.set_ylabel(val)
            self.reset_data2()
        def reset_data1(self):
            l1.set_xdata(self.t1)
            l1.set_ydata(self.data1)
            ax1.set_xlim(self.ts, self.te)
            max_range = max(self.data1) - min(self.data1)
            ax1.set_ylim(min(self.data1) - 0.05 * max_range, max(self.data1) + 0.05 * max_range)
            plt.draw()
        def reset_data2(self):
            l2.set_xdata(self.t2)
            l2.set_ydata(self.data2)
            ax2.set_xlim(self.ts, self.te)
            max_range = max(self.data2) - min(self.data2)
            ax2.set_ylim(min(self.data2) - 0.05 * max_range, max(self.data2)  + 0.05 * max_range)
            plt.draw()

    #CallBack
    update = Update(tlist,mcl.x()[1], mcl.x()[0], mcl.y()[1], mcl.y()[0])
    som1.on_changed(update.slider_start)
    som2.on_changed(update.slider_end)
    text_box1.on_submit(update.submit1)
    text_box2.on_submit(update.submit2)
    plt.show()