#coding=utf-8
import sys
import os
import threading
import SerialCom

# qt related import 
from PyQt5.QtGui import*
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.Qt import *
from PyQt5.uic.Compiler.qtproxies import QtCore


class PrinterWidget(QWidget):
    
    def __init__(self, ui, parent=None):
        super(PrinterWidget, self).__init__(parent)
        self.graphView = QGraphicsView()
        
        self.ui = ui
        self.calibrationLineList = None
        self.svgitem = None
        self.mainLayout = QGridLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addWidget(self.graphView, 0, 0)
        self.setLayout(self.mainLayout)
        
        self.setAutoFillBackground(True)
        p = QPalette()
        p.setColor(QPalette.Background, Qt.red)
        self.setPalette(p)
        self.viewport = self.graphView.viewport()
        
    def initScene(self):
        rect = QRectF( self.graphView.rect())
        self.scene = QGraphicsScene(rect)
        self.graphView.setScene(self.scene)
        #fix the 1 pix margin of graphic view
        rcontent = self.graphView.contentsRect()
        self.graphView.setSceneRect(0, 0, rcontent.width(), rcontent.height())
        #self.graphView.setSceneRect(-1, -1, 1921,1081)
        self.graphView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.graphView.resize(1920, 1080)
        self.rcontent = rcontent
        self.scene.setBackgroundBrush(Qt.black)
        
        #init preview scene
        rect = QRectF( self.ui.graphicsView.rect())
        self.scenePreview = QGraphicsScene(rect)
        self.ui.graphicsView.setScene(self.scenePreview)
        self.graphView.setStyleSheet(u"border:1px solid black");
        
        self.scenePreview.setBackgroundBrush(Qt.gray)
    
    def showCalibration(self):
        if self.svgitem!=None:
            self.scene.removeItem(self.svgitem)
        self.pix2mm = 100 # todo: 
        caliDx = int(self.pix2mm)
        caliDy = int(self.pix2mm)
        pen = QPen(Qt.red)
        if self.calibrationLineList!=None:
            ""
        self.calibrationLineList = []
        left = self.rcontent.left()
        top = self.rcontent.top()
        right = self.rcontent.right()
        bottom = self.rcontent.bottom()
        self.showBlank()
        for i in range(left,right,caliDx):
            line = self.scene.addLine(i,top,i,bottom,pen=pen)
            self.calibrationLineList.append(line)
        for i in range(top,bottom,caliDy):
            line = self.scene.addLine(left,i,right,i,pen=pen)
            self.calibrationLineList.append(line)        
        self.scene.update()
        
    def showBlank(self):
        self.scene.clear()
        #self.svgitem = None
        self.imgitem = None

    def loadSvg(self, svgfile):
        self.svgrender = QSvgRenderer(svgfile)
        
    def showSvg(self,layer):
        if self.svgitem!=None:
            self.scene.removeItem(self.svgitem)
        self.svgitem = QGraphicsSvgItem()
        self.svgitem.setSharedRenderer(self.svgrender)
        self.svgitem.setScale(self.svgscale)
        self.svgitem.setElementId("layer%d" %layer)
        rect = self.svgitem.boundingRect()
        x0 = (self.rcontent.width() - rect.width()*self.svgscale)/2
        y0 = (self.rcontent.height() - rect.height()*self.svgscale)/2
        self.svgitem.setPos(x0,y0)
        self.scene.addItem(self.svgitem)
        
    def showImage(self,imgfile):
        if self.imgitem!=None:
            self.scene.removeItem(self.imgitem)
        pixmap = QPixmap(imgfile)
        self.imgitem = self.scene.addPixmap(pixmap)

        
        
        
    








