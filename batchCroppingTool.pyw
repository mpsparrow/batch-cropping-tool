'''
Batch Cropping Tool
Coded by Matthew S
April 2020
'''

import wx
import os
import sys
from PIL import Image, ImageChops
import time
from threading import *

class RedirectText(object):
    def __init__(self,aWxTextCtrl):
        self.out = aWxTextCtrl

    def write(self,string):
        self.out.WriteText(string)

class Crop(Thread):
    def __init__(self, inputDir, outputDir, subDir, double, bottom, outer, offset, other):
        Thread.__init__(self)
        self.inputDir = inputDir
        self.outputDir = outputDir
        self.subDir = subDir
        self.doubleCrop = double
        self.bottomCrop = bottom
        self.outerCrop = outer
        self.offset = offset
        self.mainframe = other
        self._want_abort = False
        self.start()

    def trim(self, im):
        bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, self.offset * (-1))
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)

    def run(self):
        try:
            startTime = time.time()

            # makes output folder if it doesn't exist
            try:
                os.mkdir(self.outputDir)
            except:
                pass

            if self.subDir:
                arr = []
 
                for dir_, _, files in os.walk(self.inputDir):
                    for file_name in files:
                        rel_dir = os.path.relpath(dir_, self.inputDir)
                        rel_file = os.path.join(rel_dir, file_name)
                        arr.append(rel_file)
            else:
                arr = os.listdir(self.inputDir)

            # removes folders from listdir
            print(arr)
            newArr = []
            fileTypes = [".jpg", ".jpeg", ".png"]
            for item in arr:
                if any(ext in item for ext in fileTypes):
                    newArr.append(item)
            arr = newArr

            totalImages = len(arr)

            print("== Images ==")
            print(arr, "\n")
            print("== Starting Processing ==")

            counter = 0

            for itr in arr:
                cropTime = time.time()
                counter += 1
                x = 1
                if self.doubleCrop:
                    x = 0
                imgPath = os.path.join(self.inputDir, itr)
                bg = Image.open(imgPath) # The image to be cropped
                width, height = bg.size 

                if self.bottomCrop != 0:
                    bg = bg.crop((0, 0, width, height-self.bottomCrop))

                if self.outerCrop != 0:
                    bg = bg.crop((self.outerCrop, self.outerCrop, width-self.outerCrop, height-self.outerCrop))

                while x < 2:
                    x += 1
                    try:
                        bg = self.trim(bg)
                    except:
                        pass

                try:
                    os.mkdir(os.path.join(self.outputDir, os.path.dirname(itr)))
                except:
                    pass

                try:
                    bg.save(os.path.join(self.outputDir, itr))
                except:
                    bg = Image.open(imgPath)
                    bg.save(os.path.join(self.outputDir, itr))
                print(imgPath, "|", int((time.time() - cropTime)*1000), "ms")
                self.mainframe.updateProgress(counter, totalImages, startTime)

                if self._want_abort:
                    self.mainframe.result(self, "Aborted")
                    return

            secondTime = round((time.time() - startTime), 2)
            self.mainframe.result(self, f"Completed | Time: {secondTime}s | Image(s): {counter}")
        except:
            self.mainframe.worker = None
            self.mainframe.result(self, "Failed")
            return

    def abort(self):
        """abort worker thread."""
        # Method for use by main thread to signal an abort
        self._want_abort = True


class ExampleFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="Batch Cropping Tool", style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

        self.panel = wx.Panel(self)     
        self.inputLabel = wx.StaticText(self.panel, label="Input Folder")
        self.inputField = wx.TextCtrl(self.panel)
        self.inputButton = wx.Button(self.panel, label="Browse")
        self.inputButton.Bind(wx.EVT_BUTTON, self.inputFolder)

        self.outputLabel = wx.StaticText(self.panel, label="Output Folder")
        self.outputField = wx.TextCtrl(self.panel)
        self.outputButton = wx.Button(self.panel, label="Browse")
        self.outputButton.Bind(wx.EVT_BUTTON, self.outputFolder)

        self.bottomCropLabel = wx.StaticText(self.panel, label="Crop Bottom By")
        self.bottomCrop = wx.SpinCtrl(self.panel)
        self.bottomCrop.SetValue(0)
        self.outerCropLabel = wx.StaticText(self.panel, label="Crop All Sides By")
        self.outerCrop = wx.SpinCtrl(self.panel)
        self.outerCrop.SetValue(0)
        self.subDir = wx.CheckBox(self.panel, label="Include Sub-Directories")
        self.doubleCrop = wx.CheckBox(self.panel, label="Double Crop")
        self.offsetLabel = wx.StaticText(self.panel, label="Cropping Offset (tolerance)")
        self.offset = wx.SpinCtrl(self.panel)
        self.offset.SetValue(50)

        self.runBatch = wx.Button(self.panel, label="Run Batch")
        self.runBatch.Bind(wx.EVT_BUTTON, self.run)
        self.abortBatch = wx.Button(self.panel, label="Abort")
        self.abortBatch.Bind(wx.EVT_BUTTON, self.abort)

        self.log = wx.TextCtrl(self.panel, size=(300, 150), style=wx.TE_MULTILINE|wx.TE_READONLY)
        redir = RedirectText(self.log)
        sys.stdout = redir

        self.status = wx.StaticText(self.panel)

        self.progress = wx.Gauge(self.panel, range=25)

        # Set sizer for the frame, so we can change frame size to match widgets
        self.windowSizer = wx.BoxSizer()
        self.windowSizer.Add(self.panel, 1, wx.ALL | wx.EXPAND)        

        # Set sizer for the panel content
        self.sizer = wx.GridBagSizer(7, 10)
        self.sizer.Add(self.inputLabel, (0, 0), flag=wx.LEFT|wx.TOP, border=10)
        self.sizer.Add(self.inputField, (0, 1), (1, 8), flag=wx.TOP|wx.EXPAND, border=5)
        self.sizer.Add(self.inputButton, (0, 9), flag=wx.TOP|wx.RIGHT, border=5)
        
        self.sizer.Add(self.outputLabel, (1, 0), flag=wx.TOP|wx.LEFT, border=10)
        self.sizer.Add(self.outputField, (1, 1), (1, 8), flag=wx.TOP|wx.EXPAND, border=5)
        self.sizer.Add(self.outputButton, (1, 9), flag=wx.TOP|wx.RIGHT, border=5)

        self.sizer.Add(self.bottomCropLabel, (2, 1))
        self.sizer.Add(self.bottomCrop, (2, 2))
        self.sizer.Add(self.subDir, (2, 4))
        self.sizer.Add(self.outerCropLabel, (3, 1))
        self.sizer.Add(self.outerCrop, (3, 2))
        self.sizer.Add(self.doubleCrop, (3, 4))
        self.sizer.Add(self.offsetLabel, (4, 1))
        self.sizer.Add(self.offset, (4, 2))

        self.sizer.Add(self.status, (5, 0), (1, 7), flag=wx.TOP|wx.EXPAND, border=5)
        self.sizer.Add(self.runBatch, (5, 8), border=5)
        self.sizer.Add(self.abortBatch, (5, 9), border=5)

        self.sizer.Add(self.progress, (6, 0), (1, 10), flag=wx.ALL | wx.EXPAND)
        self.sizer.Add(self.log, (7, 0), (1, 10), flag=wx.ALL | wx.EXPAND)

        # Set simple sizer for a nice border
        self.border = wx.BoxSizer()
        self.border.Add(self.sizer, 1, wx.ALL | wx.EXPAND, 5)

        # Use the sizers
        self.panel.SetSizerAndFit(self.border)  
        self.SetSizerAndFit(self.windowSizer)  

        self.worker = None

    def run(self, event):
        if not self.worker:
            self.progress.SetValue(0)
            self.status.SetLabel("Running...")
            self.worker = Crop(self.inputField.GetValue(), self.outputField.GetValue(), self.subDir.GetValue(), self.doubleCrop.GetValue(), self.bottomCrop.GetValue(), self.outerCrop.GetValue(), self.offset.GetValue(), self)

    def abort(self, event):
        if self.worker:
            self.status.SetLabel("Aborting...")
            self.worker.abort()
            self.worker = None

    def result(self, event, message):
        self.status.SetLabel(message)
        self.worker = None

    def updateProgress(self, cur, final, timeElapsed):
        x = int((cur/final)*25)
        timeE = round(time.time() - timeElapsed, 2)
        self.status.SetLabel(f"{cur}/{final} | {int((cur/final)*100)}% | Time Elapsed: {int(timeE)}s | Est. Time Left: {int((timeE/cur)*(final - cur))}s")
        self.progress.SetValue(x)

    def inputFolder(self, event):
        dlg = wx.DirDialog(self, "Pick an input folder", style=wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            self.dir_path = dlg.GetPath()
            self.inputField.SetLabel(self.dir_path)

        dlg.Destroy()

    def outputFolder(self, event):
        dlg = wx.DirDialog(self, "Pick an output folder", style=wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            self.dir_path = dlg.GetPath()
            self.outputField.SetLabel(self.dir_path)

        dlg.Destroy()

app = wx.App(False)
frame = ExampleFrame(None)
frame.Show()
app.MainLoop()
