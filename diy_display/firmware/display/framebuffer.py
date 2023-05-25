import asyncio
import adafruit_framebuf

class WaveshareFramebuffer(adafruit_framebuf.FrameBuffer):
    """A driver for waveshare epaper displays"""

    def __init__(self, epd, background_img):
        self.epd = epd
        self.counter = 0
        self.full_update_every = 300

        # prealloc for when we write the display
        self._buf = bytearray(1)

        if epd.width%8 == 0:
            linewidth = int(epd.width/8)
        else:
            linewidth = int(epd.width/8) + 1
        self.buffer = bytearray(linewidth * epd.height)

        super().__init__(self.buffer, epd.width, epd.height, buf_format=adafruit_framebuf.MHMSB, stride=128)
        
        self._load_bg(background_img)

        # prepare for partial updates
        if self.bg_buf is not None:
            asyncio.get_event_loop().run_until_complete(self.epd.displayPartBaseImage(self.bg_buf))
        else:
            asyncio.get_event_loop().run_until_complete(self.epd.displayPartBaseImage(self.buffer))

    def _load_bg(self, background_img):
        '''load pbm file as bytearray and set as bg buffer'''
        try:
            with open(background_img, 'rb') as f:
                bg = bytearray(f.read())

            bg = bg[57:] # trim off header
            # invert the image
            for i, v in enumerate(bg):
                bg[i] = 0xFF & ~v
            
            self.bg_buf = bg
        except:
            self.bg_buf = None

    async def show(self):
        """write out the frame buffer over SPI via WaveShare driver"""
        
        # combine with bg
        if self.bg_buf is not None:
            for i, v in enumerate(self.buffer):
                self.buffer[i] = v & self.bg_buf[i]
        
        if self.counter >= self.full_update_every:
            await self.epd.display(self.bg_buf)
            await self.epd.displayPartBaseImage(self.bg_buf)
            await self.epd.displayPartial(self.buffer)

            self.counter = 0
        else:
            await self.epd.displayPartial(self.buffer)
            self.counter += 1

