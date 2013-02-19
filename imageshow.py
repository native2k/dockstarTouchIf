#!/usr/bin/env python

"""This is a small script to demonstrate using Tk to show PIL Image objects.
The advantage of this over using Image.show() is that it will reuse the
same window, so you can show multiple images without opening a new
window for each image.

This will simply go through each file in the current directory and
try to display it. If the file is not an image then it will be skipped.
Click on the image display window to go to the next image.

Noah Spurrier 2007
"""

import os, sys, itertools
import Tkinter
import Image, ImageTk, tkFont, tkMessageBox
from pprint import pformat
import traceback
import time
import random
import Logging

SIZE = 800, 600, 100, 100
WAIT = 1000*3
PATH = '.'
DIRECTORY = [path for path, dirs, files in os.walk(PATH) if '/.' not in path]

L = Logging.getLogger('ImageShow')

def button_click_exit_mainloop (event):
    event.widget.quit() # this will cause mainloop to unblock.

N = 12
def increment():
    global N
    N += 1
    return ' jjeayy N %s ' % N
   

class ShowImageApp(Tkinter.Frame):
    wgButton = None
    
    def __init__(self, root, config, onQuit = None, logger = None, statusFunc = None):
        self._config = config
        size = [int(e) for e in self._config['main'].get('size', SIZE)][:2]
        self.statusFunc = statusFunc
        
        Tkinter.Frame.__init__(self, root)
        self.log = logger or Logging.getLogger(self.__class__.__name__)
        self.updating = False

        self.old_image = None
        self.old_time = None
        self.old_date = None
        self.old_status = None
        
        self.dir = None
        self.dirlist = None

	self.root = root
        self.image = Tkinter.Canvas(self.root, width=size[0], height=size[0],  bg="black", bd=0)
        try:
            self.image['cursor'] ="@nullCursor white"
        except Exception, e:
            self.log.warning("unable to set cursor: %s" %  e)
        
        self.image.pack()
        self.onQuit = onQuit
        self.image.bind('<Button>', self.quitting)
            
        dirs = self._config['image'].get('dirs', './')
        self.dirs = isinstance(dirs, list) and dirs  or [dirs]
        self.wait = int(self._config['image'].get('wait', WAIT))
        self.size = size

	self.update_clock()
        self.update_time()
        #self.image.bind("<Button>", self.showDialog)

    def quitting(self, event = None):
        st = self.image.create_text(40, 100, fill='lightgrey', anchor=Tkinter.NW, font=("Purisa", 30), text=' .. QUTTING .... ', tags=('status'))
        if self.onQuit:
            self.onQuit()
        else:
            self.quit()
            
    def showDialog(self, event):
        self.log.debug('Window was clicked')

        res = tkMessageBox.askyesno(
            "quit",
            "quit to main menue"
        )
        self.log.debug('Result; %s' % res)
        if res:
            self.quit()
        # if not self.wgButton:
        #     self.wgButton = Tkinter.Button(self.image, text = '  EXIT  ', font = tkFont.Font(family="Helvetica", size=40), command = self.quit)
        #     self.wgButton.pack()
        #     self.image.after(3000, self.deletDialog)
        #self.wgScrollbar.place(bordermode=Tkinter.OUTSIDE, height= sizey-sHeight-seHeight, width=nbHeight,x = lWidth-nbHeight, y = 0)
            
    def deletDialog(self):
        if self.wgButton:
            self.log.debug('destroy window')
            self.wgButton.destroy()
            self.wgButton = None
            self.update()
            
    def destroy(self):
        self.image.destroy()
        return Tkinter.Frame.destroy(self)

    def isImageFile(self, filename):
        ufile = filename.lower()
        for ft in ['jpg', 'jpeg', 'png']:
            if '.%s' % ft in ufile:
                return True
        return False

    def getImages(self):
        if not self.dir:
            self.dir = self.dirs[:]
            random.shuffle(self.dir)
        self.log.noisy("Dirs: %s" % self.dir)
        dir = self.dir.pop()
        self.dirlist = [os.sep.join([dir, f]) for f in os.listdir(dir) if self.isImageFile(f)]
        random.shuffle(self.dirlist)
        self.log.noisy("Images: %s" % self.dirlist)

    def update_clock(self):
	self.update()
	self.image.after(self.wait, self.update_clock)

    def update_time(self):
        if not self.updating:
            self.time()
        self.image.after(1000, self.update_time)

    def time(self, alsoDate = False):
        # wait for finishing paint
        if self.statusFunc:
            try:
                statustext = self.statusFunc()
            except Exception, e:
                statustext = 'statusError: %s' % e
            st = self.image.create_text(40, 40, fill='lightgrey', anchor=Tkinter.NW, font=("fixed", 16), text=statustext, tags=('status'))
            if self.old_status:
                self.image.delete(self.old_status)
            self.old_status = st
        
	timestr = time.strftime('%H:%M:%S')
        ct = self.image.create_text(40, 500, fill='white', anchor=Tkinter.NW, font=("Purisa", 36, 'bold'), text=timestr, tags=('time'))

        #self.image.itemconfigure('time', fill='blue')

        if self.old_time:
            self.image.delete(self.old_time)
        self.old_time = ct

        if alsoDate:
            ### update date only on new imag
            if self.old_date:
                self.image.delete(self.old_date)
            datestr = time.strftime('%d.%m.%y')
            self.old_date = self.image.create_text(100, 560, fill='white', anchor=Tkinter.NW,
                                        font=("Purisa", 16, 'bold'), text=datestr, tags=('time'))




    def update(self, countExp = 0):
        # if countExp > 10:
        #     print "Maximal Error %s reached .. stop " % countExp
        #     self.image.quit()
        #     return

        while not self.dirlist:
            self.getImages()
        f = self.dirlist.pop()
        self.log.noisy("%s -> %s" % (self.dirlist, f))
        self.updating = True
	try:
            self.log.debug("Filename %s" % f)
    	    image1 = Image.open(f)
	    image1 = self.resizeImage(image1, self.size, (0.1, 0.1))

    	    tkpi = ImageTk.PhotoImage(image1)
            ic = self.image.create_image(0,0, anchor=Tkinter.NW, image = tkpi)
            if self.old_image:
                self.image.delete(self.old_image)
                #self.image.itemconfigure(self.old_image, image = tkpi)

            self.old_image = ic

            self.currentImage = tkpi
    	    #root.mainloop() # wait until user clicks the window
            self.time(True)
	except Exception, e:
    	    # This is used to skip anything not an image.
    	    # Image.open will generate an exception if it cannot open a file.
    	    # Warning, this will hide other errors as well.
    	    self.log.error("Excption: %s" % e)
    	    traceback.print_exc()
    	    self.update(countExp + 1)
        self.updating = False

    def resizeImage(self, aImage, targetSize, extremeRange  = None, bgcolor = None):
        L = self.log

        if not extremeRange:
            if targetSize[0] > targetSize[1]:
                extremeRange = (1, None)
            else:
                extremeRange = (None, 1)

        elif not isinstance(extremeRange, (tuple, list)):
            extremeRange = (extremeRange, extremeRange)

        def cropIt(img):
            newSize = img.size
            if newSize != targetSize: # need to crop
                L.noisy("need to crop -> %s (should: %s)" % (img.size, targetSize))
                diff = [(newSize[i] - targetSize[i])/2 for i in xrange(2)]
                cropp = (diff[0], diff[1], diff[0] + targetSize[0], diff[1] + targetSize[1])
                return img.crop(cropp)
            return img

        def resizeIt(img, multi):
            newSize = [int(img.size[i] * multi) for i in xrange(2)]
            L.noisy("resiztIt to -> %s " %(newSize, ))
            return img.resize(newSize, Image.ANTIALIAS)

        def fillAll(img, multi):
            L.noisy("-> fillAll (%s)" % multi)
            resImage = resizeIt(img, multi)
            return cropIt(resImage)

        def aspectRatio(img, multi, bgcolor):
            L.noisy("-> aspectRation (%s)" % multi)
            smallImg = resizeIt(img, multi)
            # if not bgcolor:
            #     ## search for must color
            #     hist = smallImg.histogram()
            #     bgcolor = max(set(hist), key=hist.count)
            #     maxocur = hist.count(bgcolor)
            #     if L.isEnabledFor('noisy'):
            #         format = "%%10d [%%-%ds]" % maxocur
            #         for color in set(hist):
            #             L.noisy(format % (color, '#' * hist.count(color)))

            #     L.noisy("Histogram: %s" % pformat(L))
            #     L.noisy("max  occur: %s" % bgcolor)

            bigImg = Image.new(img.mode, targetSize) #, bgcolor)
            xypos = tuple([int(bigImg.size[i] - smallImg.size[i])/2 for i in xrange(2)])
            L.noisy("Pos: %s  bigSize: %s smallSize %s" % (xypos, bigImg.size, smallImg.size))
            bigImg.paste(smallImg, xypos)
            return bigImg

        def enlargeIt(img):
            if True in [img.size[i] < targetSize[i] for i in xrange(2)]:
                L.debug( 'Image too small')
                multi = max([targetSize[i]/ img.size[i] for i in xrange(2)])
                return resizeIt(img, multi)
            return img

        def handleImage(img, posIdx):
            dirs = ['landscape', 'portrait']
            if extremeRange[posIdx] is None :
                raise Exception('%s Image - ignore it' % dirs[posIdx])

            resImage = enlargeIt(img)
            L.debug("%s Image -> %s (orig: %s)" % (dirs[posIdx], resImage.size, img.size))

            multit = [float(targetSize[i])/resImage.size[i] for i in xrange(2)]
            difval = abs(multit[0] - multit[1])
            L.noisy("Multi: %s -> %s" % (multit, difval))
            if difval < extremeRange[posIdx]:
                return fillAll(resImage, max(multit))
            else:
                return aspectRatio(resImage, min(multit), bgcolor)

        L.noisy("Extreme Range: %s" % (extremeRange, ))
        return handleImage(aImage, int(aImage.size[0] < aImage.size[1]))


if __name__ == "__main__":
    config = {
        'mpd' : {
            'host' : 'serverb.fritz.box',
            'port' : '6600'},
        'main': {
            'loglevel' : 'debug',
            'logfile': 'stdio',
            'size': (800, 600),
            'pos' : (100,100)},
        'image' : {
            'wait' : 10000,
            'path' : './',},
        }

    Logging.startLoggingTo('ImageShow', config.get('main',{}).get('logfile'),
                           config.get('main',{}).get('loglevel'))
    config['image']['dirs'] =  [path for path, dirs, files in os.walk(config['image'].get('path', './')) if '/.' not in path]
    SIZE = tuple([int(e) for e in (config['main'].get('size', (800,600)) + config['main'].get('pos', (0,0)))])
    root = Tkinter.Tk()
    root.overrideredirect(True)
    root.config(bg="black")
    #root.bind("<Button>", button_click_exit_mainloop)
    root.geometry('%dx%d+%d+%d' % SIZE)
    root.title('image clock')

    app = ShowImageApp(root, config)
    app.mainloop()
    root.destroy()











