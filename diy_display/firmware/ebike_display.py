import asyncio
from display.epd2in13_V3 import EPD
from display.framebuffer import WaveshareFramebuffer


MAX_CURRENT = 35
MAX_BATTERY_VOLTS = 58
MIN_BATTERY_VOLTS = 44

def motor_power_round(motor_power):

    if motor_power < 10:
        motor_power = 0
    elif motor_power < 100:
        motor_power = motor_power - (motor_power % 5)
    elif motor_power < 200:
        motor_power = motor_power - (motor_power % 10)
    elif motor_power < 300:
        motor_power = motor_power - (motor_power % 15)
    elif motor_power < 400:
        motor_power = motor_power - (motor_power % 20)
    else:
        motor_power = motor_power - (motor_power % 25)

    return int(motor_power)


def human_power(ebike_data):
    human_power = 0.105 * ebike_data.torque_weight * ebike_data.cadence
    return human_power


class EBikeDisplay():
    def __init__(self):
        self.epd = EPD()
        asyncio.get_event_loop().run_until_complete(self.init_display())
        self.framebuf = WaveshareFramebuffer(self.epd, "display/background.pbm")
        self.framebuf.rotation = 1

    async def init_display(self):
        await self.epd.init()
        await self.epd.Clear(0xFF)
        await self.epd.ReadBusy()

    async def update(self, ebike_data):
        self.framebuf.fill(1)

        max_bar_height = 110
        current_bar_height = int((ebike_data.motor_current / MAX_CURRENT) * max_bar_height)
        battery_bar_height = int(((ebike_data.battery_voltage - MIN_BATTERY_VOLTS) / (MAX_BATTERY_VOLTS - MIN_BATTERY_VOLTS)) * max_bar_height)
        self.framebuf.rect(2, 112-current_bar_height, 29, current_bar_height, 0, fill=True)
        self.framebuf.rect(219, 112-battery_bar_height, 29, battery_bar_height, 0, fill=True)

        self.framebuf.text(f"{ebike_data.motor_current:2}", 5, 93, -1, size=2)
        self.framebuf.text(f"{ebike_data.battery_voltage:2}", 222, 93, -1, size=2)

        self.framebuf.text(str(ebike_data.assist_level), 112, 7, 0, size=5)
        self.framebuf.text("00", 108, 101, 0, size=3)
        
        self.framebuf.text(f"{motor_power_round(ebike_data.motor_power):3}", 48, 14, 0, size=2)
        self.framebuf.text(f"{human_power(ebike_data): 3}", 167, 14, 0, size=2)

        # "{(ebike_data.vesc_temperature_x10 / 10.0): 2}"
        self.framebuf.text(f"{(ebike_data.motor_temperature_sensor_x10 / 10.0): 2}", 55, 90, 0, size=2)
        self.framebuf.text(f"{ebike_data.cadence: 2}", 173, 90, 0, size=2)

        if ebike_data.brakes_are_active:
            self.framebuf.text("brakes", 113, 80, 0, size=2)

        if ebike_data.vesc_fault_code:
            self.framebuf.text(f"mot e: {ebike_data.vesc_fault_code}", 113, 80, 0, size=2)

        await self.framebuf.show()



