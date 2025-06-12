# import roboticstoolbox as rtb
# from roboticstoolbox.backends.swift import Swift
# from roboticstoolbox.backends.PyPlot import PyPlot
# class Arm:
#     def __init__(self) -> None:
#         self.robot = rtb.models.SeerArm()
#         self.env_swift = Swift()
#         self.env_pyplot = PyPlot()
#         self.robot.q = self.robot.qz
#         self.show_flag = False
#     def show(self):
#         self.env_swift.launch("Arm")
#         self.env_swift.add(self.robot)
#         self.env_pyplot.launch("Arm")
#         self.env_pyplot.add(self.robot)
#         self.show_flag = True
#     def isShow(self):
#         return self.show_flag
#     def plot(self, left_q:[], right_q:[]):
#         print("left right length: ", len(left_q), len(right_q))
#         if len(left_q) == 7:
#             self.robot.q[2:9] = left_q
#         if len(right_q) == 7:
#             self.robot.q[9:16] = right_q
#         self.env_swift.step()
#         self.env_pyplot.step()

# if __name__ == '__main__':
#     a = Arm()
#     a.show()
#     a.plot([], [])
#     import time
#     while True:
#         time.sleep(1.0)

