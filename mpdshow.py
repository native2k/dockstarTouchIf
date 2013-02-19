#!/usr/bin/python

from pprint import pprint, pformat
import mpd as mpdlib
import Tkinter
import Logging

import tkFont

SIZE = 800, 600, 1000, 100


def time2str(tval):
    return '%d:%0.2d' % (tval/60, tval%60)
       
class MpdStatus(object):
    def __init__(self, config, logger = None):
        self._config = config
        self.log = logger or Logging.getLogger(self.__class__.__name__)
        
        self.mpd = mpdlib.MPDClient()
        self._host = self._config['mpd'].get('host','localhost')
        self._port = int(self._config['mpd'].get('port','6600'))
        self._connect()
        
    def _connect(self):
        self.mpd.timeout = 10
        self.mpd.idletimeout = None
        try:
            self.mpd.connect(self._host, self._port)
            if self.mpd.mpd_version:
                self.log.info('connected to mpd on %s:%s (ver %s)' % (self._host, self._port, self.mpd.mpd_version))
            self.lastStatus = self.mpd.status()
        except Exception, e:
            self.log.error('unable to connect to mpd %s:%s  %s' % (self._host, self_port, e))

    def printStatus(self):
        status = self.mpd.status()
        csong = self.mpd.currentsong()
        tlen = 20
        
        res = []
        if csong:
            res.append(csong.get('title', 'no Titlename'))
            if status['state'] in ['play']:
                sformat = '%s [%s%s] %s'
                tarray = [float(s) for s in status['time'].split(':')]
                plen = tlen / tarray[1] * tarray[0]
                tstr = sformat % (time2str(tarray[0]), '='*int(plen), '--'*(tlen - int(plen)), time2str(tarray[1]) )
                self.log.debug(tstr)
                res.append(tstr)
            else:
                res.append(status['state'])
        else:
            res.append(status['state'])
        return '\n'.join(res)

    def destroy(self):
        self.mpd.close()
        self.mpd.disconnect()
        

class MpdControl(Tkinter.Frame):
    ssize = 0.1
    lastPlaylistlength = 0
    def __init__(self, master=None, config = None, logger = None, onQuit = None):
        self._config = config or {}
        self.onQuit = onQuit
        
        size = self._config.get('main', {}).get('size', (800, 600))
        Tkinter.Frame.__init__(self, master, width= int(size[0]), height=int(size[1]))
        self.pack()

        self.log = logger or Logging.getLogger(self.__class__.__name__)
        #self.log.debug(self._config)
        
        self.mpd = mpdlib.MPDClient()
        self._host = self._config['mpd'].get('host','localhost')
        self._port = int(self._config['mpd'].get('port','6600'))

        self._connect()
        self.wxListDataRef = []
        self.wxListDataModus = 'play'
        
        self.createWidgets()
        self.widgets = {}
        
        self.updateWidgets()
        self.runUpdateSongProgress()

        try:
            self['cursor'] ="@nullCursor white"
        except Exception, e:
            self.log.warning("unable to set cursor: %s" %  e)
        
    def _connect(self):
        self.mpd.timeout = 10
        self.mpd.idletimeout = None
        try:
            self.mpd.connect(self._host, self._port)
            if self.mpd.mpd_version:
                self.log.info('connected to mpd on %s:%s (ver %s)' % (self._host, self._port, self.mpd.mpd_version))
            self.lastStatus = self.mpd.status()
        except Exception, e:
            self.log.error('unable to connect to mpd %s:%s  %s' % (self._host, self_port, e))

    def destroy(self):
        self.mpd.close()
        self.mpd.disconnect()
        Tkinter.Frame.destroy(self)
        

    def togglePlayPause(self):
        self.log.info('toggle play pause')
        if self.lastStatus['state'] == 'play':
            self.mpd.pause()
        else:
            self.mpd.play()
        self.updateWidgets()

    def stop(self):
        self.mpd.stop()
        self.updateWidgets()

    def next(self):
        self.mpd.next()
        self.updateWidgets()

    def prev(self):
        self.mpd.previous()
        self.updateWidgets()
        
    def toggleRandom(self):
        self.log.info('toogle random')
        self.mpd.random(int(not int(self.lastStatus['random'])))
        self.updateWidgets()

    def buildPlaylistList(self):
        return [ dict(id = 'p:%s' % p['playlist'], type = 'playlist', name = p['playlist'])
                 for p in self.mpd.listplaylists()] + [
                 dict(id = 'g:%s' % p, type = 'genre', name = p)
                 for p in self.mpd.list('genre') if p and "\\" not in p]
                

    def updatePlaylistInfo(self):
        self.wgListData.delete(0, Tkinter.END)
        self.wxListDataRef =[]
        # action, getlist, id, format, fields
        REF = {'play' : (self.mpd.playlistinfo, 'id','%s', ('title',)),
               'output' : (self.mpd.outputs, 'outputid', '%s:%s', ('outputid', 'outputname')),
               'playlist': (self.buildPlaylistList, 'id', '[%s] %s', ('type', 'name'))}
        ref = REF[self.wxListDataModus]
        for pos, title in enumerate(ref[0]()):
            self.wgListData.insert(pos, ref[2] % tuple([title.get(i,'') for i in ref[3]])) 
            self.wxListDataRef.append(title[ref[1]])

        #self.log.info("DataRef: %s" % self.wxListDataRef)
                                                
    def listItemSelected(self, event):
        item = event.widget.nearest(event.y)
        itemId = self.wxListDataRef[item]
        self.log.info('Item selecte in list -> %s - %s' % (item, itemId))
        if self.wxListDataModus == 'play':
            self.mpd.playid(itemId)
        elif self.wxListDataModus == 'output':
            toutput = self.mpd.outputs()[item]
            if toutput['outputenabled'] == '1':
                self.mpd.disableoutput(itemId)
            else:
                self.mpd.enableoutput(itemId)
        elif self.wxListDataModus == 'playlist':
            if self._deletPlaylist:  # only clear on first add
                self.mpd.clear()
                self._deletPlaylist = False
                
            dtype = itemId[0]
            dname = itemId[2:]
            if dtype == 'p':
                self.mpd.load(dname)
            elif dtype == 'g':
                #self.mpd.findadd('genre', dname)
                # workarround for misssing findadd command
                for f in self.mpd.find('genre',dname):
                    self.mpd.add(f['file'])
            
        self.updateWidgets()

    def outputButton(self):
        if self.wxListDataModus == 'output':
            self.wxListDataModus = 'play'
        else:
            self.wxListDataModus = 'output'
        self.updatePlaylistInfo()


    def playListButton(self):
        if self.wxListDataModus == 'playlist':
            self.wxListDataModus = 'play'
        else:
            self.wxListDataModus = 'playlist'
            self._deletPlaylist = True
        self.updatePlaylistInfo()

    def moveSongeProgress(self, cmd, svalue, sunit = None):
        status = self.mpd.status()
        tarray = [int(i) for i in status['time'].split(':')]
        
        if cmd == Tkinter.SCROLL:
            dval = sunit == Tkinter.PAGES and 30 or 10
            if svalue > 0:
                spos = min(tarray[0] + dval, tarray[1])
            else:
                spos = max(tarray[0] - dval, tarray[1])
        elif cmd == Tkinter.MOVETO:
            spos =  float(svalue) * float(tarray[1]) / (1.0 - self.ssize)  
        self.mpd.seek(status['song'], '%d' % int(spos))
        
    def runUpdateSongProgress(self):
        status = self.mpd.status()
        if status['state'] in ['play','pause']:
            self.after(1000, self.runUpdateSongProgress)
        else:
            self.after(5000, self.runUpdateSongProgress)
        self.updateSongProgress(status)
        
    def updateSongProgress(self, status):
         
        if status.get('time'):
            tarray = [float(i) for i in status['time'].split(':')]
            self.wgSongElapsed['text'] = time2str(tarray[0])
            self.wgSongLength['text'] = time2str(tarray[1])
            spos = (1.0-self.ssize)*tarray[0]/tarray[1]
            self.wgSongProgress.set(spos, spos+self.ssize)
        else:
            self.wgSongElapsed['text'] = ''
            self.wgSongLength['text'] = ''
            self.wgSongProgress.set(0.0, 1.0)

    def updateWidgets(self, update = False):
        self.after(10000, self.updateWidgets)
        status = self.lastStatus = self.mpd.status()
        status['outputs'] = self.mpd.outputs()
        status['currentSong'] = self.mpd.currentsong()
        status['stats'] = self.mpd.stats()
        output = [o for o in enumerate(status['outputs']) if o[1]['outputenabled'] == '1']

        if self.log.isEnabledFor('debug'):
            self.log.debug('mpdStatus: %s' % pformat(status))
        
        self.wgPlayPause['text'] = status['state']  == 'play' and 'pause' or 'play'
        self.wgOutput['text'] = "Outputs: %s" % ", ".join([o[1]['outputid'] for o in output])
        self.wgPlaylist['text'] = "Playlist (%s)" % status['playlistlength']
        self.wgRandom['text'] = "Random: %s" % bool(int(status['random']))

        
        sid = None
        if self.wxListDataModus == 'play':
            if self.lastPlaylistlength != status['playlistlength']:
                self.lastPlaylistlength = status['playlistlength']
                self.updatePlaylistInfo()
            if status.get('currentSong'):
                sid = self.wxListDataRef.index(status['currentSong']['id'])
        elif self.wxListDataModus == 'output':
            sid = [o[0] for o in output]
                
        if sid is not None:
            ## clear first
            for i in self.wgListData.curselection():
                self.wgListData.select_clear(i)

            # select it
            if isinstance(sid, list):
                for isid in sid:
                    self.wgListData.see(isid)
                    self.wgListData.select_set(isid)
            else:
                self.wgListData.see(sid)
                self.wgListData.select_set(sid)

        # update songprogress
        self.updateSongProgress(status)
         
        if status.get('error'):
            self.wgStatus['text'] = str(status['error'])
        elif status['state'] in ['play', 'pause']:
            self.wgStatus['text'] = '%s => %s [%s]\n%s - no: %s, %s' % (
                status['state'].upper(), status['currentSong'].get('title', 'NO SONGTITLE'), status['currentSong'].get('artist', ''),
                status['currentSong'].get('album',''), status['currentSong'].get('track', ''), status['currentSong'].get('genre',''))
        else:
            self.wgStatus['text'] = ''

    def quitting(self):
        self.wgStatus['text'] = 'QUITTING ..... '
        if self.onQuit:
            self.onQuit()
        else:
            self.quit()

    def createWidgets(self):

        self.customFont = tkFont.Font(family="Helvetica", size=16)
        self.customFontText = tkFont.Font(family="Helvetica", size=12)

        #self.wgUp = Tkinter.Button(self, text = 'up', font = self.customFont)
        #self.wgDown = Tkinter.Button(self, text = 'down', font = self.customFont)
        self.wgScrollbar = Tkinter.Scrollbar(self, orient = Tkinter.VERTICAL)

        self.wgNext = Tkinter.Button(self, text = '>>', font = self.customFont, command = self.next)
        self.wgPrev = Tkinter.Button(self, text = '<<', font = self.customFont, command = self.prev)
                                             
        self.wgStop = Tkinter.Button(self, text = 'stop', font = self.customFont, command = self.stop)
        self.wgPlayPause = Tkinter.Button(self, text = 'Play', font = self.customFont, command = self.togglePlayPause)

        self.wgPlaylist = Tkinter.Button(self, text = 'PL:<empty>', font = self.customFontText, command = self.playListButton)
        #self.wgPlaylistText = Tkinter.Label(self, text = 'first Playlsit', bg='white', font = self.customFontText)
        self.wgOutput = Tkinter.Button(self, text = 'OP:<empty>', font = self.customFontText, command = self.outputButton)
        #self.wgOutputText = Tkinter.Label(self, text = 'default', bg='white', font = self.customFontText)
        self.wgRandom = Tkinter.Button(self, text = 'Random:', font = self.customFontText, command = self.toggleRandom)

        self.wgSongElapsed = Tkinter.Label(self, text = '0:00', font = self.customFontText)
        self.wgSongLength = Tkinter.Label(self, text = '00:00', font = self.customFontText)
        self.wgSongProgress = Tkinter.Scrollbar(self, orient = Tkinter.HORIZONTAL, jump = 1, command = self.moveSongeProgress)
            
        self.QUIT = Tkinter.Button(self, text = 'quit', font = self.customFont, command = self.quitting)

        self.wgStatus = Tkinter.Label(self, text = 'yeahhh\n ups', bg='white', font = self.customFontText)
        self.wgListData = Tkinter.Listbox(self, font = self.customFontText, yscrollcommand=self.wgScrollbar.set)
        self.wgListData.bind("<Button>", self.listItemSelected)
        self.wgScrollbar.config(command = self.wgListData.yview)
        

        
        sizex, sizey = 800, 600
        lWidth = 500 # list width
        nbHeight = 30 # navigation height
        sHeight = 50 # status height

        bHeight, bWidth  = 60, 100 # button height, width
        lSpace = 30

        seWidth = 80
        seHeight = 25

        # self.wgUp.pack()
        # self.wgUp.place(bordermode=Tkinter.OUTSIDE, height=nbHeight, width=lWidth, x = 0, y = 0)
        # self.wgDown.pack()
        # self.wgListData.pack()
        # self.wgListData.place(bordermode=Tkinter.OUTSIDE, height= sizey-sHeight-2*nbHeight, width=lWidth,
        #                       x = 0, y = nbHeight)
        # self.wgDown.place(bordermode=Tkinter.OUTSIDE, height=nbHeight, width=lWidth, x = 0,
        #                   y = sizey-sHeight-nbHeight)

        self.wgScrollbar.pack()
        self.wgScrollbar.place(bordermode=Tkinter.OUTSIDE, height= sizey-sHeight-seHeight, width=nbHeight,
                           x = lWidth-nbHeight, y = 0)
        self.wgListData.pack()
        self.wgListData.place(bordermode=Tkinter.OUTSIDE, height= sizey-sHeight-seHeight, width=lWidth-nbHeight,
                           x = 0, y = 0)
        

        self.wgSongElapsed.pack()
        self.wgSongElapsed.place(bordermode=Tkinter.OUTSIDE, height= seHeight, width=seWidth,
                           x = 0, y = sizey-sHeight-seHeight) 
        self.wgSongLength.pack()
        self.wgSongLength.place(bordermode=Tkinter.OUTSIDE, height= seHeight, width=seWidth,
                           x = sizex - seWidth, y = sizey-sHeight-seHeight)
        self.wgSongProgress.pack()
        self.wgSongProgress.place(bordermode=Tkinter.OUTSIDE, height= seHeight, width=sizex - seWidth*2,
                           x = seWidth, y = sizey-sHeight-seHeight)
       
        
        self.wgStatus.pack()
        self.wgStatus.place(bordermode=Tkinter.OUTSIDE, height=sHeight, width=sizex, x = 0, y = sizey-sHeight)

        self.QUIT.pack()
        self.QUIT.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=bWidth*2,
                        x = lWidth +lSpace*2, y = sizey - sHeight - bHeight - lSpace)

        self.wgPrev.pack()
        self.wgPrev.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=bWidth,
                          x = lWidth + lSpace, y = lSpace + bHeight*4)
        self.wgNext.pack()
        self.wgNext.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=bWidth,
                               x = lWidth + 2*lSpace + bWidth, y = lSpace + bHeight*4)


        self.wgStop.pack()
        self.wgStop.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=bWidth,
                          x = lWidth + lSpace, y = lSpace*2 + bHeight*5)
        self.wgPlayPause.pack()
        self.wgPlayPause.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=bWidth,
                               x = lWidth + 2*lSpace + bWidth, y = lSpace*2 + bHeight*5)

        self.wgPlaylist.pack()
        self.wgPlaylist.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=sizex - lSpace*2 - lWidth,
                          x = lSpace + lWidth, y = lSpace)
        self.wgOutput.pack()
        self.wgOutput.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=sizex - lSpace*2 - lWidth,
                            x = lSpace + lWidth, y = lSpace + bHeight)

        self.wgRandom.pack()
        self.wgRandom.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=sizex - lSpace*2 - lWidth,
                            x = lSpace + lWidth, y = lSpace + 2*bHeight)

        #self.wgPlaylistText.pack()
        #self.wgPlaylistText.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=sizex - lSpace*2 - lWidth,
        #                          x = lWidth + lSpace, y = lSpace + bHeight*5)
        # self.wgOutputText.pack()
        # self.wgOutputText.place(bordermode=Tkinter.OUTSIDE, height=bHeight, width=bWidth,
        #                        x = lWidth + 2*lSpace + bWidth, y = lSpace + bHeight*6)
        


if __name__ == "__main__":
    config = {
        'mpd' : {
            'host' : 'serverb.fritz.box',
            'port' : '6600'},
        'main': {
            'loglevel' : 'debug',
            'logfile': 'stdio',
            'size': (800, 600),
            'pos' : (0,0)}
        }

    Logging.startLoggingTo('ImageShow', config.get('main',{}).get('logfile'),
                           config.get('main',{}).get('loglevel'))

    root = Tkinter.Tk()
    root.overrideredirect(True)
    #root.config(bg="black")
    #root.bind("<Button>", button_click_exit_mainloop)
    root.geometry('%dx%d+%d+%d' % SIZE)
    root.title('mpd control')

    app = MpdControl(root, config)
    app.mainloop()
    root.destroy()



