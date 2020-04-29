import wx
import os
from PIL import Image, ImageChops
import time
from threading import *

class Crop(Thread):
    def __init__(self, inputDir, outputDir, subDir, double, bottom, outer, other):
        Thread.__init__(self)
        self.inputDir = inputDir
        self.outputDir = outputDir
        self.subDir = subDir
        self.doubleCrop = double
        self.bottomCrop = bottom
        self.outerCrop = outer
        self.mainframe = other
        self._want_abort = False
        self.start()

    def trim(self, im):
        bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)

    def run(self):
        try:
            startTime = time.time()

            print("== Setup ==")

            # makes output folder if it doesn't exist
            try:
                os.mkdir(self.outputDir)
                print("Output Directory Created:", self.outputDir, "\n")
            except:
                print("Output Directory Already Exists:", self.outputDir, "\n")

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
            for item in arr:
                if "." in item:
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

                if self.bottomCrop:
                    bg = bg.crop((0, 0, width, height-1))

                if self.outerCrop:
                    bg = bg.crop((1, 1, width-1, height-1))

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
                print(imgPath, " Time:", int((time.time() - cropTime)*1000), "ms")
                self.mainframe.updateProgress(counter, totalImages)

                if self._want_abort:
                    print("== Aborted ==")
                    self.mainframe.result(self, "Aborted")
                    return

            print("\n== Done ==")
            secondTime = round((time.time() - startTime), 2)
            self.mainframe.result(self, f"Completed | Time: {secondTime}s | Image(s): {counter}")
        except:
            print("\n== Failed ==")
            self.mainframe.worker = None
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

        self.subDir = wx.CheckBox(self.panel, label="Include Sub-Directories")
        self.doubleCrop = wx.CheckBox(self.panel, label="Double Crop")
        self.bottomCrop = wx.CheckBox(self.panel, label="Crop Bottom by 1")
        self.outerCrop = wx.CheckBox(self.panel, label="Crop All Sides by 1")

        self.runBatch = wx.Button(self.panel, label="Run Batch")
        self.runBatch.Bind(wx.EVT_BUTTON, self.run)
        self.abortBatch = wx.Button(self.panel, label="Abort")
        self.abortBatch.Bind(wx.EVT_BUTTON, self.abort)

        self.status = wx.StaticText(self.panel)

        self.progress = wx.Gauge(self.panel, range=25)

        # Set sizer for the frame, so we can change frame size to match widgets
        self.windowSizer = wx.BoxSizer()
        self.windowSizer.Add(self.panel, 1, wx.ALL | wx.EXPAND)        

        # Set sizer for the panel content
        self.sizer = wx.GridBagSizer(5, 10)
        self.sizer.Add(self.inputLabel, (0, 0), flag=wx.LEFT|wx.TOP, border=10)
        self.sizer.Add(self.inputField, (0, 1), (1, 8), flag=wx.TOP|wx.EXPAND, border=5)
        self.sizer.Add(self.inputButton, (0, 9), flag=wx.TOP|wx.RIGHT, border=5)
        
        self.sizer.Add(self.outputLabel, (1, 0), flag=wx.TOP|wx.LEFT, border=10)
        self.sizer.Add(self.outputField, (1, 1), (1, 8), flag=wx.TOP|wx.EXPAND, border=5)
        self.sizer.Add(self.outputButton, (1, 9), flag=wx.TOP|wx.RIGHT, border=5)

        self.sizer.Add(self.subDir, (2, 1))
        self.sizer.Add(self.doubleCrop, (2, 3))
        self.sizer.Add(self.bottomCrop, (3, 1))
        self.sizer.Add(self.outerCrop, (3, 3))

        self.sizer.Add(self.status, (4, 0), (1, 7), flag=wx.TOP|wx.EXPAND, border=5)
        self.sizer.Add(self.runBatch, (4, 8), border=5)
        self.sizer.Add(self.abortBatch, (4, 9), border=5)

        self.sizer.Add(self.progress, (5, 0), (1, 10), flag=wx.ALL | wx.EXPAND)

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
            self.worker = Crop(self.inputField.GetValue(), self.outputField.GetValue(), self.subDir.GetValue(), self.doubleCrop.GetValue(), self.bottomCrop.GetValue(), self.outerCrop.GetValue(), self)

    def abort(self, event):
        if self.worker:
            self.status.SetLabel("Aborting...")
            self.worker.abort()
            self.worker = None

    def result(self, event, message):
        self.status.SetLabel(message)
        self.worker = None

    def updateProgress(self, cur, final):
        x = int((cur/final)*25)
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
