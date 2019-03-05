# LogReader
从log文件中读取IMU, Odometer, MCLoc, Send, Get, Laser, fatal, error, warning and notice信息

使用环境Python 3, 推荐使用[Anaconda](https://www.anaconda.com/download/)
* get_report.py 为生成错误报告的脚本。在命名窗口输入:<pre><code>python test_get_report.py test1.log test2.log</pre></code>
  将test1.log和test2.log替换为所需的log文件即可

  **将release中的get_report.exe置于rbk目录下，运行get_report.exe可以自动读取diagnosis\\log下的log文件，并生成报告**
* test.py 为调用 loglib.py的示例。在命名窗口输入:<pre><code>python test.py test1.log test2.log</pre></code>
 test1.log, test2.log 为测试读取的log

* loggui.py 为PyQt5图形化的log解析器
  * 使用方式：直接运行即可
  * 支持两条曲线比较
  * 支持时间窗口选取
  * 支持定位(mcl), 里程(odo), 惯性传感器(imu), 下发速度(send), 获取速度(get)
  * Evaluate可以输入的参数:
    * 定位: mcl.x, mcl.y, mcl.theta, mcl.confidence
    * 惯性传感器: imu.yaw, imu.ax, imu.ay, imu.gz, imu.gx, imu.gy, imu.gz, imu.offx, imu.offy, imu.offz
    * 里程: odo.x, odo.y, odo.theta, odo.stop,  odo.vx, odo.vy, odo.vw, odo.steer_angle, odo.encode0, odo.encode1, odo.encode2, odo.encode3
    * 下发速度: send.vx, send.vy, send.vw, send.steer_angle, send.max_vx, send.max_vw
    * 获取速度：get.vx, get.vy, get.vw, get.steer_angle, get.max_vx, get.max_vw
    * 激光里程: laserOdo.ts, laserOdo.x, laserOdo.y, laserOdo.angle
    * 电池数据：battery.percentage, battery.current, battery.voltage, battery.ischarging, battery.temperature, battery.cycle
    * 控制器数据: controller.tmp, controller.humi, controller.emc, controller.brake, controller.driveremc, controller.autocharge, controller.electric
    * 阻挡障碍物信息: stop.x, stop.y, stop.type, stop.id, stop.dist
    * 减速障碍物信息: slowdown.x, slowdown.y, slowdown.type, slowdown.id, slowdown.dist
    * 传感器融合信息: sensorfuser.localnum, sensorfuser.globalnum
    * 手动的速度数据: manual.vx, manual.vy, manual.vw, steer_angle
    * 激光雷达的数据: laser.ts
* 图形界面截图

![screen shot](screen_shot.PNG)