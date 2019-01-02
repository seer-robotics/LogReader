from loglib import MCLoc, IMU, Odometer, Send, Get, Laser, ErrorLine, WarningLine, ReadLog, FatalLine, AlarmLine
from loglib import findrange
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider,Button
import sys
mcl = MCLoc()
imu = IMU()
odo = Odometer()
send = Send()
get = Get()
laser = Laser(1000.0)
err = ErrorLine()
war = WarningLine()
fatal = FatalLine()
alarm = AlarmLine()
# for file in files:
# #    log = ReadLog("log/robokit_2018-12-27_11-05-54.87.log")
#     log = ReadLog(file)
#     log.parse(mcl, imu, odo, send, get, laser, err, war)
#     print(file,":")
#     print(max(imu.offx()) - min(imu.offx()), " ", max(imu.offy()) - min(imu.offy()), " ", max(imu.offz()) - min(imu.offz()))
log = ReadLog(sys.argv[1:])
log.parse(mcl, imu, odo, send, get, laser, err, war,fatal, alarm)

f = open("Report.txt", "w", encoding='utf-8') 
print(len(fatal.content()), "FATALs", len(err.content()), " ERRORs, ", len(war.content()), " WARNINGs", len(alarm.content()), "ALARMs", file = f )
print("FATALs:", file = f)
for data in fatal.content():
    print(data,file = f)
print("ERRORs:", file = f)
for data in err.content():
    print(data,file = f)
print("WARNINGs:", file = f)
for data in war.content():
    print(data, file = f)
print("ALARMs:", file = f)
for data in alarm.content():
    print(data, file = f)
f.close()


if len(mcl.t()) > 0:
    fig = plt.figure(1)
    ax = plt.axes([0.1, 0.2, 0.8, 0.3])
    #画图 mcl.t, mcl.x
    l1, = plt.plot(mcl.t(), mcl.x(), '.')
    plt.grid()
    ax_xy = plt.axes([0.1, 0.55, 0.8, 0.3])
    #画图 mcl.t, mcl.x
    l_xy, = plt.plot(mcl.x(), mcl.y(), '.')
    plt.grid()

    #slider
    axcolor = 'lightgoldenrodyellow'  # slider的颜色
    om1= plt.axes([0.1, 0.1, 0.8, 0.05], facecolor=axcolor) # 第一slider的位置
    som1 = Slider(om1, r'Start',0, len(mcl.t())-1, valinit=0) #产生第一slider
    # slider的val text 重写
    som1.valtext.set_text("")
    som1.valtext = om1.text(0.02, 0.5, mcl.t()[0].strftime("%H:%M:%S.%f"),
                        transform=om1.transAxes,
                        verticalalignment='center',
                        horizontalalignment='left')
    som1.valtext.set_text(mcl.t()[0].strftime("%H:%M:%S.%f"))
    om2= plt.axes([0.1, 0.02, 0.8, 0.05], facecolor=axcolor) # 第一slider的位置
    som2 = Slider(om2, r'End', 1, len(mcl.t())-1, valinit=len(mcl.t())-1) #产生第一slider
    # slider的val text 重写
    som2.valtext.set_text("")
    som2.valtext = om2.text(0.02, 0.5, mcl.t()[-1].strftime("%H:%M:%S.%f"),
                        transform=om2.transAxes,
                        verticalalignment='center',
                        horizontalalignment='left')
    # Button
    tx = 0.0
    tdx = 0.03
    mcl_x_ax = plt.axes([tx, 0.9, 0.03, 0.03])
    mcl_x_bt = Button(mcl_x_ax, 'x')
    mcl_y_ax = plt.axes([tx+tdx, 0.9, 0.03, 0.03])
    mcl_y_bt = Button(mcl_y_ax, 'y')
    mcl_theta_ax = plt.axes([tx+2*tdx, 0.9, 0.03, 0.03])
    mcl_theta_bt = Button(mcl_theta_ax, r"$\theta$")
    mcl_confidence_ax = plt.axes([tx+3*tdx, 0.9, 0.03, 0.03])
    mcl_confidence_bt = Button(mcl_confidence_ax, r"C")

    class Update:
        def __init__(self,t,data,x,y):
            self.ind1 = 0
            self.ind2 = len(t)-1 
            self.t = t
            self.ts = t[0]
            self.te = t[-1]
            self.data = data
            self.x = x
            self.y = y 
        def slider_start(self, event):
            print("slider start event = ",event)
            self.ind1 = int(som1.val)
            if self.ind1 >= self.ind2 :
                self.ind1 = self.ind2 - 1
                som1.set_val(self.ind1)
            self.ts = self.t[self.ind1]
            som1.valtext.set_text(self.t[self.ind1].strftime("%H:%M:%S.%f"))
            ax.set_xlim(self.t[self.ind1], self.t[self.ind2])
            l_xy.set_xdata(self.x[self.ind1:self.ind2])
            l_xy.set_ydata(self.y[self.ind1:self.ind2])
        def slider_end(self, event):
            print("slider end event = ",event)
            self.ind2 = int(som2.val)
            if self.ind1 >= self.ind2 :
                self.ind2 = self.ind1 + 1
                som2.set_val(self.ind2)
            self.te = self.t[self.ind2]
            som2.valtext.set_text(self.t[self.ind2].strftime("%H:%M:%S.%f"))
            ax.set_xlim(self.t[self.ind1], self.t[self.ind2])
            l_xy.set_xdata(self.x[self.ind1:self.ind2])
            l_xy.set_ydata(self.y[self.ind1:self.ind2])
        def up_mcl_x(self, event):
            print("button event = ",event)
            self.t = mcl.t()
            self.data = mcl.x()
            self.ind1, self.ind2 = findrange(self.t, self.ts, self.te)
            self.reset_data()
        def up_mcl_y(self, event):
            print("button event = ",event)
            self.t = mcl.t()
            self.data = mcl.y()
            self.ind1, self.ind2 = findrange(self.t, self.ts, self.te)
            self.reset_data()
        def up_mcl_theta(self, event):
            print("button event = ",event)
            self.t = mcl.t()
            self.data = mcl.theta()
            self.ind1, self.ind2 = findrange(self.t, self.ts, self.te)
            self.reset_data()
        def up_mcl_confidence(self, event):
            print("button event = ",event)
            self.t = mcl.t()
            self.data = mcl.confidence()
            self.ind1, self.ind2 = findrange(self.t, self.ts, self.te)
            self.reset_data()
        def reset_data(self):
            som1.set_val(self.ind1)
            som2.set_val(self.ind2)
            som1.valtext.set_text(self.t[self.ind1].strftime("%H:%M:%S.%f"))
            som2.valtext.set_text(self.t[self.ind2].strftime("%H:%M:%S.%f"))
            l1.set_xdata(self.t[self.ind1:self.ind2])
            l1.set_ydata(self.data[self.ind1:self.ind2])
            ax.set_xlim(self.t[self.ind1], self.t[self.ind2])
            ax.set_ylim(min(self.data), max(self.data))

    #CallBack
    update = Update(mcl.t(),mcl.x(),mcl.x(),mcl.y())
    som1.on_changed(update.slider_start)
    som2.on_changed(update.slider_end)
    mcl_x_bt.on_clicked(update.up_mcl_x)
    mcl_y_bt.on_clicked(update.up_mcl_y)
    mcl_theta_bt.on_clicked(update.up_mcl_theta)
    mcl_confidence_bt.on_clicked(update.up_mcl_confidence)
    plt.show()