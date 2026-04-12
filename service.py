import xbmc
import urllib.request
import xbmcaddon
import xbmcgui

# --- Configuration ---
ADDON = xbmcaddon.Addon()

CMD_STRAIGHT = "7E81E01F"
CMD_7CH_STEREO = "7E81FF00"
CMD_INFO = "7F01609F"
CMD_EXIT = "7A85AA55"
last_file = "none"
last_channel = 0
title_pause = ADDON.getLocalizedString(32006)
title_caption = ADDON.getLocalizedString(32007)

internet_protocols = ('http://', 'https://', 'rtsp://')

def send_yamaha_command(code,ip):
    url = f"http://{ip}/YamahaExtendedControl/v1/system/sendIrCode?code={code}"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            pass
    except Exception as e:
        xbmc.log(f"YAMAHA-SERVICE {ip} Error: {e}", xbmc.LOGERROR)

def send_yamaha_oldschool(is_straight,ip):
    URL = f"http://{ip}/YamahaRemoteControl/ctrl"
    m7ch = """<YAMAHA_AV cmd="PUT"><Main_Zone><Surround><Program_Sel><Current><Sound_Program>7ch Stereo</Sound_Program></Current></Program_Sel></Surround></Main_Zone></YAMAHA_AV>"""
    mstr = """<YAMAHA_AV cmd="PUT"><Main_Zone><Surround><Program_Sel><Current><Straight>On</Straight></Current></Program_Sel></Surround></Main_Zone></YAMAHA_AV>"""
    DSP = mstr if is_straight else m7ch

    try:
        req = urllib.request.Request(URL, data=DSP.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'text/xml; charset=utf-8')
        
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        xbmc.log(f"YAMAHA-SERVICE {ip} Error: {e}", xbmc.LOGERROR)

class YamahaService(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.monitor = xbmc.Monitor()

    def pausewhilestopped(self, seconds):
        for _ in range(seconds * 10): # 100ms increments
            if self.monitor.abortRequested():
                return False
            if self.isPlaying(): # If a new video started during the wait
                return False
            xbmc.sleep(100)
        return True

    def pausewhileplay(self, seconds):
        for _ in range(seconds * 10): # 100ms increments
            if self.monitor.abortRequested():
                return False
            if not self.isPlaying(): # If a new video started during the wait
                return False
            xbmc.sleep(100)
        return True


    def _cleanup_receiver(self, event_type):
        global last_file
        global last_channel

        self.pausewhilestopped(10)
        if not self.isPlaying():
            last_channel = 0
            last_file = "none"
            YIP = ADDON.getSetting('yamaha_ip')
            got_multicast = ADDON.getSettingBool('got_multicast')
            
            try:
                if got_multicast :
                    send_yamaha_command(CMD_STRAIGHT,YIP)
                    xbmc.log(f"YAMAHA-SERVICE: {event_type} : Multicast - Set Default Mode : STRAIGHT", xbmc.LOGINFO)
                else:
                    send_yamaha_oldschool(True,YIP)
                    xbmc.log(f"YAMAHA-SERVICE: {event_type} : YNC - Set Default Mode : STRAIGHT", xbmc.LOGINFO)
                    
            except Exception as e:
                xbmc.log(f"YAMAHA-CLEANUP-ERROR: {e}", xbmc.LOGERROR)
    
    def onPlayBackStopped(self):
        self._cleanup_receiver("STOPPED")
        
    def onPlayBackEnded(self):
        self._cleanup_receiver("ENDED")
            
    def onAVStarted(self):
        global last_file
        global last_channel
        
        paused = False
        YIP = ADDON.getSetting('yamaha_ip')
        got_multicast = ADDON.getSettingBool('got_multicast')
        SHOW_ONSCREEN = (ADDON.getSettingBool('show_onscreen') and got_multicast)
        PAUSE = int(ADDON.getSetting('video_pause') or 0)
        ONSCREEN = int(ADDON.getSetting('screen_seconds') or 0)

        #xbmc.log(f"YAMAHA-SERVICE: {YIP} : ShowScreen: {SHOW_ONSCREEN} Wait: {PAUSE} Show: {ONSCREEN}", xbmc.LOGINFO)
        xbmc.log("YAMAHA-SERVICE: Playback started, fetching audio channel info", xbmc.LOGINFO)
        
        channels = ""
        retries = 0
        max_retries = 60 # Wait up to 15 seconds for spin-up
        
        while not channels and retries < max_retries:
            # Check for abort so we don't hang if the user stops the movie while spinning up
            if xbmc.Monitor().abortRequested():
                return
            
            if self.isPlayingVideo():    
                channels = xbmc.getInfoLabel('VideoPlayer.AudioChannels')
            else:
                channels = 2
                
            if not channels:
                retries += 1
                xbmc.sleep(250) # Wait 1 second before checking again
        
        #xbmc.log(f"YAMAHA-SERVICE: Got Metadata!", xbmc.LOGINFO)
        if channels:
            if int(channels) != last_channel :
                last_channel = int(channels)
                xbmc.log(f"YAMAHA-SERVICE: {channels} audio channels found : {retries} retries", xbmc.LOGINFO)
                if int(channels) <= 2:
                    if got_multicast :
                        send_yamaha_command(CMD_7CH_STEREO,YIP)
                        xbmc.log("YAMAHA-SERVICE: Multicast - Mode: 7ch Stereo", xbmc.LOGINFO)
                    else :
                        send_yamaha_oldschool(False,YIP)
                        xbmc.log("YAMAHA-SERVICE: YNC - Mode: 7ch Stereo", xbmc.LOGINFO)
                else:
                    if got_multicast :
                        send_yamaha_command(CMD_STRAIGHT,YIP)
                        xbmc.log("YAMAHA-SERVICE: Multicast - Mode: Straight", xbmc.LOGINFO)
                    else :
                        send_yamaha_oldschool(True,YIP)
                        xbmc.log("YAMAHA-SERVICE: YNC - Mode: Straight", xbmc.LOGINFO)
        
            curr_file = self.getPlayingFile()   #xbmc.getInfoLabel('Player.Filename')
            xbmc.log(f"YAMAHA-SERVICE: Path/File - {curr_file}", xbmc.LOGINFO)
            if self.isPlayingVideo() and curr_file != last_file :
                if PAUSE > 0 and not curr_file.lower().startswith(internet_protocols):
                    xbmc.log(f"YAMAHA-SERVICE: Pausing for {PAUSE} seconds", xbmc.LOGINFO)
                    self.pause()
                    secs = self.getTime()
                    if secs < 60 : self.seekTime(0.0)
                    paused = True
                    xbmcgui.Dialog().notification(title_pause,title_caption, xbmcgui.NOTIFICATION_INFO, PAUSE*1000)
                    self.pausewhileplay(PAUSE)
                else:
                    xbmc.log(f"YAMAHA-SERVICE: Skipping pause - No Pause set or Internet Stream", xbmc.LOGINFO)
                    
                if self.isPlaying():
                    if paused and xbmc.getCondVisibility("Player.Paused"): 
                        self.pause()
                        xbmc.log(f"YAMAHA-SERVICE: Play resumed", xbmc.LOGINFO)
                    if SHOW_ONSCREEN and ONSCREEN>0:
                        xbmc.log(f"YAMAHA-SERVICE: Showing Yamaha AV Info Screen for {ONSCREEN} seconds", xbmc.LOGINFO)
                        send_yamaha_command(CMD_INFO,YIP)
                        self.pausewhileplay(ONSCREEN)
                        send_yamaha_command(CMD_EXIT,YIP)
            else:
                xbmc.log("YAMAHA-SERVICE: Skipping pause and on-screen - Not video or repeat video", xbmc.LOGINFO)
            last_file = curr_file
#            except:
#                pass
        else:
            xbmc.log("YAMAHA-SERVICE: Timeout waiting for drive spin-up.", xbmc.LOGERROR)


# Keep the service alive
if __name__ == '__main__':
    monitor = xbmc.Monitor()
    player_monitor = YamahaService()
    
    xbmc.log("YAMAHA-SERVICE: Background service started", xbmc.LOGINFO)
    
    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break

    xbmc.log("YAMAHA-SERVICE: Background service stopping", xbmc.LOGINFO)