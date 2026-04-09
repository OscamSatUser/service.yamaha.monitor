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

def send_yamaha_command(code,ip):
    url = f"http://{ip}/YamahaExtendedControl/v1/system/sendIrCode?code={code}"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
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
            xbmc.log(f"YAMAHA-SERVICE: {event_type} - Default back to STRAIGHT...", xbmc.LOGINFO)
            
            try:
                send_yamaha_command(CMD_STRAIGHT,YIP)
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
        SHOW_ONSCREEN = ADDON.getSettingBool('show_onscreen')
        PAUSE = int(ADDON.getSetting('screen_delay') or 0)
        ONSCREEN = int(ADDON.getSetting('screen_seconds') or 0)

        xbmc.log(f"YAMAHA-SERVICE: {YIP} : ShowScreen: {SHOW_ONSCREEN} Wait: {PAUSE} Show: {ONSCREEN}", xbmc.LOGINFO)
        xbmc.log("YAMAHA-SERVICE: Playback started, waiting for metadata...", xbmc.LOGINFO)
        
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
                xbmc.log(f"YAMAHA-SERVICE: Metadata found after {retries}s. Channels: {channels}", xbmc.LOGINFO)
                if int(channels) <= 2:
                    xbmc.log("YAMAHA-DEBUG: Mode: 7ch Stereo", xbmc.LOGINFO)
                    send_yamaha_command(CMD_7CH_STEREO,YIP)
                else:
                    xbmc.log("YAMAHA-DEBUG: Mode: Straight", xbmc.LOGINFO)
                    send_yamaha_command(CMD_STRAIGHT,YIP)
        
            curr_file = xbmc.getInfoLabel('Player.Filename')
            #xbmc.log(f"YAMAHA-DEBUG: {curr_file}", xbmc.LOGINFO)            
            if SHOW_ONSCREEN and self.isPlayingVideo() and curr_file != last_file :
                xbmc.log(f"YAMAHA-DEBUG: Showing Yamaha Screen in {PAUSE} seconds", xbmc.LOGINFO)
                if self.isPlayingVideo():
                    self.pause()
                    secs = self.getTime()
                    if secs < 60 : self.seekTime(0.0)
                    paused = True
                    xbmcgui.Dialog().notification('Waiting pause time', 'or Press Play', xbmcgui.NOTIFICATION_INFO, PAUSE*1000)
                    self.pausewhileplay(PAUSE)
                
                if self.isPlaying():
                    if paused and xbmc.getCondVisibility("Player.Paused"): self.pause()
                    send_yamaha_command(CMD_INFO,YIP)
                    self.pausewhileplay(ONSCREEN)
                    send_yamaha_command(CMD_EXIT,YIP)
            else:
                xbmc.log("YAMAHA-DEBUG: Skipping Yamaha Screen", xbmc.LOGINFO)
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