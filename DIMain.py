# -*- coding: utf-8 -*-
# Image Loader for Dlp printer
# by riven 2016/05/25

import sys
import os
from os.path import expanduser
import threading
import SerialCom
import time
import queue
import glob

# qt related import 
from PyQt5.QtGui import*
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from DIGui import *
import printerWidget

_translate = QtCore.QCoreApplication.translate

class WorkInThread(threading.Thread):
    def __init__(self, target, *args):
        self.targetFun = target
        self.kArgs = args
        threading.Thread.__init__(self)
 
    def run(self):
        self.targetFun(*self.kArgs)

class MainUI(QWidget):
    
    robotSig = pyqtSignal(str)
    isPrinting = False
    def __init__(self,screens):
        self.filelist = None
        self.exptime = 400
        self.dz = 0.05
        super(MainUI, self).__init__()
        self.screens = screens
        print(self.screens[0].size())
        self.initUI()
         
    def initUI(self):
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        
        self.setWindowTitle("DLP Printer")
        self.show()
        
        self.ui.progressBar.setValue(0)
        # init serial
        self.comm = None
        self.serial = SerialCom.serialCom(self.commRx)
        self.refreshCom()
        self.initProjectorWindow()
        # connect buttons
        self.ui.pushButton.clicked.connect(self.loadImages)
        
        self.ui.btnRefresh.clicked.connect(self.refreshCom)
        self.ui.btnConnect.clicked.connect(self.connectPort)
        self.ui.btnPrint.clicked.connect(self.startPrint)
        
        self.ui.btnHomeZ.clicked.connect(self.G28)
        self.ui.btnUp10mm.clicked.connect(self.UP10mm)
        self.ui.btnUp1mm.clicked.connect(self.UP1mm)
        
        self.ui.btnShowCalibration.clicked.connect(self.projWidget.showCalibration)
        self.ui.btnShowBlank.clicked.connect(self.projWidget.showBlank)
        
        self.ui.sliderLayer.valueChanged.connect(self.layerChanged)
        
        self.q = queue.Queue()
        self.robotSig.connect(self.parseSig)
        
    def parseSig(self,string):
        if "layer" in string:
            layerNum = int(string[5:])
            self.ui.sliderLayer.setValue(layerNum)
            self.ui.progressBar.setValue(100.0*layerNum/len(self.filelist))
        elif "finish" in string:
            self.projWidget.showBlank()
            self.ui.progressBar.setValue(100)
        elif "blank" in string:
            self.projWidget.showBlank()

    def loadImages(self,filename):
        if filename==False:
            filename = QFileDialog.getExistingDirectory(self, u'Select Folder', '.',
                                                        QFileDialog.ShowDirsOnly)
        if len(filename)==0:
            return
        title = u'DLPPrinter  [%s]' %filename
        self.setWindowTitle(title)
        self.filelist = glob.glob(filename+"/*.png")
        self.ui.sliderLayer.setMaximum(len(self.filelist)-1)
        self.showImage(0)
    
    def showImage(self,index):
        if self.filelist == None:
            return
        self.ui.labelLayer.setText("%d/%d" %(index,len(self.filelist)-1))
        self.projWidget.showImage(self.filelist[index])
    
    def initProjectorWindow(self):
        self.projWidget = printerWidget.PrinterWidget(self.ui)
        self.projWidget.show()
        if len(self.screens)==1:
            return
        self.projWidth = self.screens[1].size().width()
        self.projHeight = self.screens[1].size().height()
        self.ui.labelProj.setText("%dx%d" %(self.projWidth, self.projHeight))
        self.projWidget.windowHandle().setScreen(self.screens[1])
        self.projWidget.showFullScreen()
        self.projWidget.initScene()
        self.projWidget.showCalibration()
        
    def layerChanged(self):
        if self.filelist == None:
            return
        layer = int(self.ui.sliderLayer.value())
        self.ui.labelLayer.setText("%d/%d" %(layer,len(self.filelist)-1))
        self.projWidget.showImage(self.filelist[layer])

    def printModelThread(self):
        if self.filelist == None:
            return
        self.isPrinting = True
        self.exptime = float(self.ui.lineExpTime.text())/1000.0
        while not self.q.empty():
            self.q.get()
        numLayers = len(self.filelist)
        posZ = 0
        self.ui.btnPrint.setText("Stop")
        for layer in range(numLayers):
            print("printing layer",layer)
            # 1 show layer image
            self.robotSig.emit("layer%d" %layer)
            self.projWidget.showImage(self.filelist[layer])
            time.sleep(self.exptime)
            self.robotSig.emit("blank")
            # 2 step move z axis
            posZ+=self.dz
            movement = "G1 Z%f\n" %(posZ)
            self.sendCmd(movement)
            self.q.get()
            
            if self.isPrinting == False:
                print("print end")
                return

    def startPrint(self):
        if self.isPrinting==False:
            self.printThread = WorkInThread(self.printModelThread)
            self.printThread.setDaemon(True)
            self.printThread.start()
        else:
            self.isPrinting = False
            self.ui.btnPrint.setText("Start Print")
            

    def commRx(self,msg):
        print("rx ",msg)
        if "ok" in msg:
            self.q.put(1)

    def connectPort(self):
        port = str(self.ui.portCombo.currentText())
        try:
            baud = int(self.ui.lineBaud.text())
            if self.commList[port] == "COM":
                self.serial.connect(port, baud)
                self.comm = self.serial
            self.ui.btnConnect.clicked.connect(self.disconnectPort)
            self.ui.btnConnect.clicked.disconnect(self.connectPort)
            self.ui.btnConnect.setText(u"Disconnect")
        except Exception as e:
            print(e)
            raise Exception(e)

    def disconnectPort(self):
        if self.comm==None:
            return
        self.comm.close()
        self.ui.btnConnect.clicked.connect(self.connectPort)
        self.ui.btnConnect.clicked.disconnect(self.disconnectPort)
        self.ui.btnConnect.setText(u"Connect")
        self.comm = None
        return

    def refreshCom(self):
        self.commList = {}
        self.ui.portCombo.clear()
        serPorts = SerialCom.serialList()
        for s in serPorts:
            self.commList[s]="COM"
            self.ui.portCombo.addItem(s)

    def sendCmd(self,cmd=""):
        if self.comm == None: return
        if cmd==False:
            cmd = str(self.ui.lineCmd.text())+'\n'
        print("tx ",cmd)
        self.comm.send(cmd)
        
    def G28(self):
        self.sendCmd("G28\n")
        
    def UP10mm(self):
        self.sendCmd("G91\nG0 Z10\n")
    
    def UP1mm(self):
        self.sendCmd("G91\nG0 Z1\n")
    
    def UP01mm(self):
        self.sendCmd("G91\nG0 Z-0.1\n")
        
    def DOWN10mm(self):
        self.sendCmd("G91\nG0 Z-10\n")
    
    def DOWN1mm(self):
        self.sendCmd("G91\nG0 Z-1\n")
    
    def DOWN01mm(self):
        self.sendCmd("G91\nG0 Z-0.1\n")
    
    def closeEvent(self, event):
        if hasattr(self, 'projWidget'):
            self.projWidget.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    screens = app.screens()
    ex = MainUI(screens)
    sys.exit(app.exec_())





