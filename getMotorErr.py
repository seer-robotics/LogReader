import MotorRead as mr
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout
from PyQt5 import QtGui, QtCore,QtWidgets
import re,json
from loglibPlus import rbktimetodate

class MotorErrViewer(QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    moveHereSignal = QtCore.pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super().__init__()
        self.lines = []
        self.title = "MotorErr"
        self.InitWindow()
        self.resize(1200,800)
        self.moveHere_flag = False
        self.mode_path = ""

    def InitWindow(self):
        self.setWindowTitle(self.title)
        vbox = QVBoxLayout()
        self.plainText = QPlainTextEdit()
        self.plainText.setPlaceholderText("This is MotorErr")
        self.plainText.setReadOnly(True)
        self.plainText.setUndoRedoEnabled(False)
        self.plainText.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.plainText.setBackgroundVisible(True)
        self.plainText.ensureCursorVisible()
        self.plainText.contextMenuEvent = self.contextMenuEvent
        
        hbox = QHBoxLayout()
        self.find_edit = QtWidgets.QLineEdit()
        self.find_up = QtWidgets.QPushButton("Up")
        self.find_up.clicked.connect(self.findUp)
        self.find_down = QtWidgets.QPushButton("Down")
        self.find_down.clicked.connect(self.findDown)
        hbox.addWidget(self.find_edit)
        hbox.addWidget(self.find_up)
        hbox.addWidget(self.find_down)
        vbox.addWidget(self.plainText)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.find_cursor = None
        self.find_set_cursor = None
        self.highlightFormat = QtGui.QTextCharFormat()
        self.highlightFormat.setForeground(QtGui.QColor("red"))
        self.plainText.cursorPositionChanged.connect(self.cursorChanged)
        self.last_cursor = None
        self.cursor_finish = False

    def setModelPath(self, path):
        self.mode_path = path
    
    def setLines(self, lines):
        self.lines = lines if lines is not None else []

    def clearPlainText(self):
        self.plainText.appendPlainText("")
    
    def listMotorErr(self):
        self.plainText.clear()
        if not self.mode_path:
            self.plainText.setPlainText("The model should be add!")
            return
        if not self.lines:
            self.plainText.setPlainText("No log data available!")
            return

        reg = re.compile("(.[a-zA-Z0-9]*-0x[a-zA-Z0-9]*)")
        model_m_b_dict = mr.getMotorNameBrandDict(self.mode_path)
        with open("ErrTab.json", "r", encoding='utf-8') as stream:
            err_tab = json.loads(stream.read())

        for raw_line in self.lines:
            if isinstance(raw_line, bytes):
                try:
                    line = raw_line.decode('utf-8')
                except UnicodeDecodeError:
                    line = raw_line.decode('gbk', errors='ignore')
            else:
                line = raw_line
            if "52135|Motor Error:" not in line or "|0]" in line:
                continue

            self.plainText.appendPlainText(
                line.replace('\n', '').replace('\r', ''))
            for count, pair in enumerate(reg.findall(line), 1):
                motor_code_list = re.split("\W", pair)
                if len(motor_code_list) < 3:
                    continue
                motor_name = motor_code_list[1]
                motor_code = motor_code_list[2]
                motor_brand = model_m_b_dict.get(motor_name)
                if motor_brand is None or motor_brand not in err_tab:
                    continue
                motor_code_number = int(motor_code, 16)
                self.plainText.appendPlainText(
                    "电机{}名字:{} 品牌:{} 错误码:{}".format(
                        count, motor_name, motor_brand, motor_code))

                brand_errors = err_tab[motor_brand]
                matched_count = 1
                for key, error_info in brand_errors.items():
                    if key == "match_bit":
                        continue
                    key_number = int(key, 16)
                    matched = ((key_number & motor_code_number) != 0
                               if brand_errors["match_bit"]
                               else key_number == motor_code_number)
                    if not matched:
                        continue
                    self.plainText.appendPlainText(
                        "    对应错误{}:{} ".format(matched_count, key))
                    self.plainText.appendPlainText(
                        "        错误描述:" + error_info["des"])
                    self.plainText.appendPlainText(
                        "        错误原因:" + error_info["reason"])
                    self.plainText.appendPlainText(
                        "        解决方法:" + error_info["method"])
                    matched_count += 1
                self.plainText.appendPlainText("")
        self.cursor_finish = True
                
    def setLineNum(self, ln):
        if not self.moveHere_flag:
            cursor = QtGui.QTextCursor(self.plainText.document().findBlockByLineNumber(ln))
            self.plainText.setTextCursor(cursor)
        else:
            self.moveHere_flag = False

    def closeEvent(self,event):
        self.plainText.appendPlainText("")
        self.hide()
        self.hiddened.emit(True)    
    
    def contextMenuEvent(self, event):
        popMenu = self.plainText.createStandardContextMenu()
        popMenu.addAction('&Move Here',self.moveHere)
        cursor = QtGui.QCursor()
        popMenu.exec_(cursor.pos()) 

    def moveHere(self):
        cur_cursor = self.plainText.textCursor()
        cur_cursor.select(QtGui.QTextCursor.LineUnderCursor)
        line = cur_cursor.selectedText()
        regex = re.compile("\[(.*?)\].*")
        out = regex.match(line)
        if out:
            self.moveHere_flag = True
            mtime = rbktimetodate(out.group(1))
            self.moveHereSignal.emit(mtime)  

    def findUp(self):
        searchStr = self.find_edit.text()
        if searchStr != "":
            doc = self.plainText.document()
            cur_highlightCursor = self.plainText.textCursor()
            if self.find_cursor:
                if self.find_set_cursor and \
                    self.find_set_cursor.position() == cur_highlightCursor.position():
                    cur_highlightCursor = QtGui.QTextCursor(self.find_cursor)
                    cur_highlightCursor.setPosition(cur_highlightCursor.anchor())                   
                
            cur_highlightCursor = doc.find(searchStr, cur_highlightCursor, QtGui.QTextDocument.FindBackward)
            if cur_highlightCursor.position() >= 0:
                if self.find_cursor:
                    fmt = QtGui.QTextCharFormat()
                    self.find_cursor.setCharFormat(fmt)
                cur_highlightCursor.movePosition(QtGui.QTextCursor.NoMove,QtGui.QTextCursor.KeepAnchor)
                cur_highlightCursor.mergeCharFormat(self.highlightFormat)
                self.find_cursor = QtGui.QTextCursor(cur_highlightCursor)
                cur_highlightCursor.setPosition(cur_highlightCursor.anchor())
                self.find_set_cursor = cur_highlightCursor
                self.plainText.setTextCursor(cur_highlightCursor)

    def findDown(self):
        searchStr = self.find_edit.text()
        if searchStr != "":
            doc = self.plainText.document()
            cur_highlightCursor = self.plainText.textCursor()
            if self.find_cursor:
                if self.find_set_cursor and \
                    cur_highlightCursor.position() == self.find_set_cursor.position():
                    cur_highlightCursor = QtGui.QTextCursor(self.find_cursor)
                    cur_highlightCursor.clearSelection()

            cur_highlightCursor = doc.find(searchStr, cur_highlightCursor)
            if cur_highlightCursor.position()>=0:
                if self.find_cursor:
                    fmt = QtGui.QTextCharFormat()
                    self.find_cursor.setCharFormat(fmt)
                cur_highlightCursor.movePosition(QtGui.QTextCursor.NoMove,QtGui.QTextCursor.KeepAnchor)
                cur_highlightCursor.setCharFormat(self.highlightFormat)
                self.find_cursor = QtGui.QTextCursor(cur_highlightCursor)
                cur_highlightCursor.clearSelection()
                self.find_set_cursor = cur_highlightCursor
                self.plainText.setTextCursor(cur_highlightCursor)
                
    def cursorChanged(self):
        if self.cursor_finish:
            fmt= QtGui.QTextBlockFormat()
            fmt.setBackground(QtGui.QColor("light blue"))
            cur_cursor = self.plainText.textCursor()
            cur_cursor.select(QtGui.QTextCursor.LineUnderCursor)
            cur_cursor.setBlockFormat(fmt)
            if self.last_cursor:
                if cur_cursor.blockNumber() != self.last_cursor.blockNumber():
                    fmt = QtGui.QTextBlockFormat()
                    self.last_cursor.select(QtGui.QTextCursor.LineUnderCursor)
                    self.last_cursor.setBlockFormat(fmt)          
            self.last_cursor = self.plainText.textCursor()

if __name__ == "__main__":
    import sys
    import os
    app = QApplication(sys.argv)
    view = MotorErrViewer()
    filenames = ["test1.log"]
    view.readFilies(filenames)
    view.show()
    app.exec_()

