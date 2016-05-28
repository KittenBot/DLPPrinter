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
    exptime = 50
    
    def __init__(self,screens):
        self.filelist = []
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
        #self.ui.btnUp10mm.clicked.connect(self.UP10mm)
        self.ui.btnUp1mm.clicked.connect(self.UP1mm)
        self.ui.btnDown1mm.clicked.connect(self.DOWN1mm)
        self.ui.btnUp10mm.clicked.connect(self.UP10mm)
        self.ui.btnDown10mm.clicked.connect(self.DOWN10mm)
        
        self.ui.btnShowCalibration.clicked.connect(self.projWidget.showCalibration)
        self.ui.btnShowBlank.clicked.connect(self.projWidget.showBlank)
        
        self.ui.lineHeight.editingFinished.connect(self.calcExptime)
        self.ui.lineFeedrate.editingFinished.connect(self.calcExptime)
        
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
        layers = len(self.filelist)
        print("total layers %d" %(layers))
        self.ui.sliderLayer.setMinimum(1)
        self.ui.sliderLayer.setMaximum(layers)
        self.ui.labelLayer.setText("%d/%d" %(1,len(self.filelist)))
        self.showImage(0)
        self.calcExptime()
    
    def showImage(self,index):
        if len(self.filelist) == 0:
            return
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
        self.ui.btnShowCalibration.setEnabled(True)
        self.ui.btnShowBlank.setEnabled(True)
        
    def layerChanged(self):
        if len(self.filelist) == 0:
            return
        layer = int(self.ui.sliderLayer.value())
        self.ui.labelLayer.setText("%d/%d" %(layer,len(self.filelist)))
        self.projWidget.showImage(self.filelist[layer-1])

    def printModelThread(self):
        if len(self.filelist) == 0:
            return
        self.isPrinting = True
        numLayers = len(self.filelist)
        posZ = 0
        self.ui.btnPrint.setText("Stop")
        delaytime = self.exptime/1000
        height = float(self.ui.lineHeight.text())
        feedrate = float(self.ui.lineFeedrate.text())
        
        if self.ui.radioDown.isChecked():
            height=-height
            
        Gcode = "G1 Z%f F%f\n" %(height,feedrate)
        self.sendCmd(Gcode)
        for layer in range(numLayers):
            self.robotSig.emit("layer%d" %layer)
            time.sleep(delaytime)
            posZ+=self.dz
            if self.isPrinting == False:
                print("print end")
                break
        self.robotSig.emit("finished")
        
    def calcExptime(self):
        if len(self.filelist) == 0:
            return
        layers = len(self.filelist)
        height = float(self.ui.lineHeight.text())
        feedrate = float(self.ui.lineFeedrate.text())
        layerHeight = height/layers
        self.ui.labelLayerHeight.setText("%04f" %layerHeight)
        self.exptime = layerHeight/(feedrate/60)*1000
        self.ui.labelExpTime.setText("%04f" %self.exptime)
        
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
        self.sendCmd("G91\nG0 Z10 F200\n")
    
    def UP1mm(self):
        self.sendCmd("G91\nG0 Z1 F200\n")
    
    def UP01mm(self):
        self.sendCmd("G91\nG0 Z-0.1 F200\n")
        
    def DOWN10mm(self):
        self.sendCmd("G91\nG0 Z-10 F200\n")
    
    def DOWN1mm(self):
        self.sendCmd("G91\nG0 Z-1 F200\n")
    
    def DOWN01mm(self):
        self.sendCmd("G91\nG0 Z-0.1 F200\n")
    
    def closeEvent(self, event):
        if hasattr(self, 'projWidget'):
            self.projWidget.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    screens = app.screens()
    ex = MainUI(screens)
    sys.exit(app.exec_())





