
# /*****************************************************************************
# * | File        :	  epdconfig.py
# * | Author      :   Waveshare team
# * | Function    :   Hardware underlying interface
# * | Info        :
# *----------------
# * | This version:   V1.2
# * | Date        :   2022-10-29
# * | Info        :   
# ******************************************************************************
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
import time
import board
from busio import SPI
import digitalio

import adafruit_logging as logging
logger = logging.getLogger(__name__)

# Pin definition
CLK_PIN = board.IO7 # clock
DIN_PIN = board.IO9 # MOSI/data in
CS_PIN = board.IO3 # chip select
DC_PIN = board.IO12 # command
RST_PIN = board.IO11 # reset
BUSY_PIN = board.IO5 # busy

SPI = SPI(CLK_PIN, DIN_PIN, None)

CS_PIN = digitalio.DigitalInOut(CS_PIN)
DC_PIN = digitalio.DigitalInOut(DC_PIN)
RST_PIN = digitalio.DigitalInOut(RST_PIN)
BUSY_PIN = digitalio.DigitalInOut(BUSY_PIN)

def digital_write(pin, value):
    #pin.switch_to_output()
    pin.value = value

def digital_read(pin):
    return pin.value

def delay_ms(delaytime):
    time.sleep(delaytime / 1000.0)

def spi_writebyte(data):
    SPI.write(bytes(data))

def spi_writebyte2(data):
    SPI.write(bytes(data))

def module_init():
    SPI.try_lock()
    SPI.configure(baudrate=4000000, phase=0, polarity=0)

    CS_PIN.direction = digitalio.Direction.OUTPUT
    DC_PIN.direction = digitalio.Direction.OUTPUT
    RST_PIN.direction = digitalio.Direction.OUTPUT
    BUSY_PIN.direction = digitalio.Direction.INPUT

    return 0

def module_exit():
    logger.debug("spi end")
    SPI.unlock()

    logger.debug("release resources")
    RST_PIN.value = 0
    DC_PIN.value = 0
    
    CS_PIN.deinit()
    DC_PIN.deinit()
    RST_PIN.deinit()
    BUSY_PIN.deinit()