import asyncio
import board
import time

from buttons import Buttons
from ebike_data import EBike
from ebike_board import EBikeBoard
from ebike_display import EBikeDisplay


ASSIST_MAX_LEVEL = 5

ebike_data = EBike()
ebike = EBikeBoard(
    board.IO18, # UART TX pin that connect to display UART RX pin
    board.IO17, # UART RX pin that connect to display UART TX pin
    ebike_data) # EBike data object to hold the EBike data

async def task_ebike_process_data():
    while True:
        ebike.process_data()
        await asyncio.sleep(0.01) # 10ms

async def task_ebike_send_data():
    while True:
        ebike.send_data()
        await asyncio.sleep(0.1) # 100ms


buttons = Buttons(
    board.IO33, # POWER
    board.IO37, # UP
    board.IO35) # DOWN

async def task_button_presses():
    while True:
        if buttons.up and ebike_data.assist_level < ASSIST_MAX_LEVEL:
            ebike_data.assist_level += 1
            while buttons.up:
                await asyncio.sleep(0.01)

        elif buttons.down and ebike_data.assist_level > 0:
            ebike_data.assist_level -= 1
            while buttons.down:
                await asyncio.sleep(0.01)

        await asyncio.sleep(0.01) # 10ms


display = EBikeDisplay()

async def task_display_update():
    prev_update = time.monotonic()
    prev_assist_level = ebike_data.assist_level
    prev_motor_current = ebike_data.motor_current
    await display.update(ebike_data)
    while True:
        now = time.monotonic()
        # high priority updates
        if ebike_data.assist_level != prev_assist_level or\
           ebike_data.motor_current != prev_motor_current or\
           (now - prev_update) > 8.0:
            # assist and current are high priority, everything else on 8 sec interval
            prev_assist_level = ebike_data.assist_level
            prev_motor_current = ebike_data.motor_current
            prev_update = now
            await display.update(ebike_data)

        await asyncio.sleep(0.01) # 10ms


async def main():
    print('main entry')

    await asyncio.gather(
            task_ebike_process_data(),
            task_ebike_send_data(),
            task_button_presses(),
            task_display_update()
            )

asyncio.run(main())