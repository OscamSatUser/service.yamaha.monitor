import xbmc
import urllib.request
import xbmcaddon

# --- Configuration ---
ADDON = xbmcaddon.Addon()

CMD_STRAIGHT = "7E81E01F"
CMD_7CH_STEREO = "7E81FF00"
CMD_INFO = "7F01609F"
CMD_EXIT = "7A85AA55"

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

    def _cleanup_receiver(self, event_type):
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
        YIP = ADDON.getSetting('yamaha_ip')
        SHOW_ONSCREEN = ADDON.getSettingBool('show_onscreen')
        PAUSE = int(ADDON.getSetting('screen_delay') or 0) * 1000
        ONSCREEN = int(ADDON.getSetting('screen_seconds') or 0) * 1000

        xbmc.log(f"YAMAHA-SERVICE: {YIP} : ShowScreen: {SHOW_ONSCREEN} Wait: {PAUSE} Show: {ONSCREEN}", xbmc.LOGINFO)
        xbmc.log("YAMAHA-SERVICE: Playback started, waiting for metadata...", xbmc.LOGINFO)
        
        channels = ""
        retries = 0
        max_retries = 15 # Wait up to 15 seconds for spin-up
        
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
                xbmc.sleep(1000) # Wait 1 second before checking again
        
        if channels:
            #xbmc.log(f"YAMAHA-SERVICE: Metadata found after {retries}s. Channels: {channels}", xbmc.LOGINFO)
            try:
                if int(channels) <= 2:
                    xbmc.log("YAMAHA-DEBUG: Mode: 7ch Stereo", xbmc.LOGINFO)
                    send_yamaha_command(CMD_7CH_STEREO,YIP)
                else:
                    xbmc.log("YAMAHA-DEBUG: Mode: Straight", xbmc.LOGINFO)
                    send_yamaha_command(CMD_STRAIGHT,YIP)
                
                #Give time for the screen resolution to update and display before showing onscreen.
                if SHOW_ONSCREEN:
                    xbmc.log(f"YAMAHA-DEBUG: Showing Yamaha Screen in {PAUSE} milliseconds", xbmc.LOGINFO)
                    if self.isPlayingVideo():
                        xbmc.sleep(PAUSE)
                    
                    if self.isPlaying():
                        send_yamaha_command(CMD_INFO,YIP)
                        xbmc.sleep(ONSCREEN)
                        send_yamaha_command(CMD_EXIT,YIP)
                else:
                    xbmc.log("YAMAHA-DEBUG: Skipping Yamaha Screen", xbmc.LOGINFO)
            except:
                pass
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