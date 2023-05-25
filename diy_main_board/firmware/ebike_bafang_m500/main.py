import board
import time
import supervisor
import array
import simpleio
import asyncio
import ebike_data
import throttle
import brake_sensor
import wheel_speed_sensor
import torque_sensor
import motor_temperature_sensor
import vesc
import display
import esp32

# Tested on a ESP32-S3-DevKitC-1-N8R2

###############################################
# OPTIONS

torque_sensor_weight_min_to_start_x10 = 40 # (value in kgs) let's avoid any false startup, we will need this minimum weight on the pedals to start
torque_sensor_weight_max_x10 = 400 # torque sensor max value is 40 kgs. Let's use the max range up to 40 kgs

motor_min_current_start = 2 # to much lower value will make the motor vibrate and not run, so, impose a min limit (??)
motor_max_current_limit = 30.0 # max value, be carefull to not burn your motor

ramp_up_time = 0.05 # ram up time for each 1A
ramp_down_time = 0.04 # ram down time for each 1A

throttle_enable = True # should throttle be used?

cranck_lenght_mm = 170

# debug options
enable_print_ebike_data_to_terminal = False
enable_debug_log_cvs = False

###############################################
#                            0   1     2    3    4    5  
assist_level_factor_table = [0, 0.5, 1.0, 2.0, 3.0, 5.0]

# open file for log data
if enable_debug_log_cvs:
    log = open("/log_csv.txt", "w")

brake_sensor = brake_sensor.BrakeSensor(
   board.IO10) # brake sensor pin

wheel_speed_sensor = wheel_speed_sensor.WheelSpeedSensor(
   board.IO46) # wheel speed sensor pin

torque_sensor = torque_sensor.TorqueSensor(
    board.IO21, # CAN tx pin
    board.IO47) # CAN rx pin
  
throttle = throttle.Throttle(
    board.IO18, # ADC pin for throttle
    min = 17500, # min ADC value that throttle reads, plus some margin
    max = 50500) # max ADC value that throttle reads, minus some margin
throttle_over_max_error = 58000 # if throttle value is over this value, something is wrong, so, stop the motor

motor_temperature_sensor = motor_temperature_sensor.MotorTemperatureSensor(
   board.IO3) # motor temperature sensor pin

esp32 = esp32.ESP32()

ebike = ebike_data.EBike()
vesc = vesc.Vesc(
    board.IO14, # UART TX pin tebike_app_datahat connect to VESC
    board.IO13, # UART RX pin that connect to VESC
    ebike) #VESC data object to hold the VESC data

display = display.Display(
    board.IO12, # UART TX pin that connect to display UART RX pin
    board.IO11, # UART RX pin that connect to display UART TX pin
    ebike)

def check_brakes():
    """Check the brakes and if they are active, set the motor current to 0
    """
    if ebike.brakes_are_active == False and brake_sensor.value == True:
        # brake / coast the motor
        vesc.brake()
        ebike.motor_current_target = 0
        ebike.brakes_are_active = True
      
    elif ebike.brakes_are_active == True and brake_sensor.value == False:
        ebike.brakes_are_active = False

def print_ebike_data_to_terminal():
    """Print EBike data to terminal
    """
    if ebike.battery_current < 0:
       ebike.battery_current = 0

    if ebike.motor_current < 0:
       ebike.motor_current = 0
  
    #print(f" m_cur_t {ebike.motor_current_target:2.1f} | m_cur {ebike.motor_current:2.1f} | b_cur {ebike.battery_current:2.1f}", end='\r')
    #print(f" trq {ebike.torque_weight_x10: 2.1f} | cad {ebike.cadence: 3} | wheel {ebike.wheel_speed}", end='\r')
    print(f"b_v {ebike.battery_voltage:2.1f} | thr {throttle.adc_value:6} | thr {(throttle.value / 10.0):2.1f} %", end='\n')
    #print(f"mot_cur {ebike.motor_current:2.1f} | b_cur {ebike.battery_current:2.1f} | b_v {ebike.battery_voltage:2.1f} | m_p {int(ebike.motor_power)}")
    #print(f"esp temp {(esp32.temperature_x10 / 10.0):3.1f} | vesc temp {(ebike.vesc_temperature_x10 / 10.0):3.1f} | {(motor_temperature_sensor.value_x10  / 10.0):3.1f}")
    
def utils_step_towards(current_value, target_value, step):
    """ Move current_value towards the target_value, by increasing / decreasing by step
    """
    value = current_value

    if current_value < target_value:
        if (current_value + step) < target_value:
            value += step
        else:
            value = target_value
    
    elif current_value > target_value:
        if (current_value - step) > target_value:
            value -= step
        else:
            value = target_value

    return value

async def task_log_data():
    while True:
        # log data to local file system CSV file
        brake = 0
        if brake_sensor.value:
            brake = 1
        log.write(f"{ebike.torque_weight_x10:.1f},{ebike.cadence},{brake},{ebike.battery_current:.1f},{ebike.motor_current:.1f}\n")
        print(supervisor.ticks_ms())

        ebike.log_flush_cnt += 1
        if ebike.log_flush_cnt > 200:
            ebike.log_flush_cnt = 0
            log.flush()

        # idle 25ms, fine tunned
        await asyncio.sleep(0.025)

async def task_display_process_data():
    while True:
        # are breaks active and we should disable the motor?
        #check_brakes()

        # need to process display data periodically
        display.process_data()

        # idle 10ms
        await asyncio.sleep(0.01)

async def task_display_send_data():
    while True:
        # are breaks active and we should disable the motor?
        #check_brakes()

        # need to process display data periodically
        display.send_data()

        # idle 100ms
        await asyncio.sleep(0.1)

async def task_vesc_heartbeat():
    while True:
        # are breaks active and we should disable the motor?
        #check_brakes()
        
        # VESC heart beat must be sent more frequently than 1 second, otherwise the motor will stop
        vesc.send_heart_beat()
        
        # ask for VESC latest data
        vesc.refresh_data()

        # let's calculate here this:
        ebike.motor_power = ebike.battery_voltage * ebike.battery_current

        # should we print EBike data to terminal?
        if enable_print_ebike_data_to_terminal == True:
            print_ebike_data_to_terminal()

        # idle 500ms
        await asyncio.sleep(0.5)


# to keep time for a timeout count
pedal_human_power__time = 0
pedal_human_power__torque_weight_array_x10 = array.array('I', (0 for _ in range(255)))
pedal_human_power__cadence_array = array.array('I', (0 for _ in range(255)))
pedal_human_power__average_counter = 0
pedal_human_power__temp_x10 = 0

def calculate_human_pedal_power(torque_weight, cadence, cranck_lenght_mm):
    global pedal_human_power__time
    global pedal_human_power__torque_weight_array_x10
    global pedal_human_power__cadence_array
    global pedal_human_power__average_counter
    global pedal_human_power__temp_x10

     # store values for later average 
    pedal_human_power__torque_weight_array_x10[pedal_human_power__average_counter] = torque_weight
    pedal_human_power__cadence_array[pedal_human_power__average_counter] = cadence
    pedal_human_power__average_counter += 1

    # ever 1 second, calculate the pedal_human_power
    now = time.monotonic()
    if now > (pedal_human_power__time + 1.0):
        pedal_human_power__time = now

        counter = pedal_human_power__average_counter
        sum_torque_weight_x10 = 0
        sum_cadence = 0
        while counter > 1:
            counter -= 1
            sum_torque_weight_x10 += pedal_human_power__torque_weight_array_x10[pedal_human_power__average_counter]
            sum_cadence += pedal_human_power__cadence_array[pedal_human_power__average_counter]

        if pedal_human_power__average_counter > 0:
            torque_weight_average_x10 = (sum_torque_weight_x10 / pedal_human_power__average_counter)
            cadence_average = (sum_cadence / pedal_human_power__average_counter)

            # Force (Nm) = weight Kg * 9.81 * arm cranks lenght
            force = torque_weight_average_x10 * 9.81 * (cranck_lenght_mm / 100.0)

            # pedal_human_power = torque * cadence * ((2 * pi) / 60) 
            # ((2 * pi) / 60) = 0.10467
            pedal_human_power__temp_x10 = int(force * cadence_average * 1.0467)

        # need to reset this
        pedal_human_power__average_counter = 0
    #print("human power: ", pedal_human_power__temp_x10 / 10.0)
    return int(pedal_human_power__temp_x10 / 10.0)

motor_current_target__torque_sensor = 0
def motor_control():
    ##########################################################################################
    # Torque sensor input processing

    # read the values from torque sensor
    torque_weight_x10, cadence = torque_sensor.value
    if torque_weight_x10 is not None:
        # store values for later usage if needed
        ebike.torque_weight_x10 = torque_weight_x10
        ebike.cadence = cadence
        #ebike.human_pedal_power = calculate_human_pedal_power(ebike.torque_weight_x10, ebike.cadence, cranck_lenght_mm)
        
        # map torque value to motor current
        motor_current_target__torque_sensor = simpleio.map_range(
            torque_weight_x10,
            torque_sensor_weight_min_to_start_x10, # min input
            torque_sensor_weight_max_x10, # max input
            0, # min output
            motor_max_current_limit) # max output

        # apply the assist level
        assist_level_factor = assist_level_factor_table[ebike.assist_level]
        motor_current_target__torque_sensor *= assist_level_factor
    ##########################################################################################

    ##########################################################################################
    # Throttle

    # map throttle value to motor current
    motor_current_target__throttle = 0
    if throttle_enable == True and throttle.adc_value < throttle_over_max_error:
        # map torque value to motor current
        motor_current_target__throttle = simpleio.map_range(
            throttle.value,
            0, # min input
            1000, # max input
            0, # min output
            motor_max_current_limit) # max output
    ##########################################################################################

    # use the max value from either torque sensor or throttle
    motor_current_target = max(motor_current_target__torque_sensor, motor_current_target__throttle)

    # save motor temperature sensor for later usage
    ebike.motor_temperature_sensor_x10 = motor_temperature_sensor.value_x10

    # impose a min motor current value, as to much lower value will make the motor vibrate and not run (??)
    if motor_current_target < motor_min_current_start:
        motor_current_target = 0

    # provide a quick way to disable the motor
    if ebike.assist_level == 0:
        motor_current_target = 0

    # apply ramp up / down factor: faster when ramp down
    if motor_current_target > ebike.motor_current_target:
        ramp_time = ramp_up_time
    else:
        ramp_time = ramp_down_time
        
    time_now = time.monotonic_ns()
    ramp_step = (time_now - ebike.ramp_last_time) / (ramp_time * 1000000000)
    ebike.ramp_last_time = time_now
    ebike.motor_current_target = utils_step_towards(ebike.motor_current_target, motor_current_target, ramp_step)

    # let's limit the value
    if ebike.motor_current_target > motor_max_current_limit:
        ebike.motor_current_target = motor_max_current_limit

    if ebike.motor_current_target < 0.0:
        ebike.motor_current_target = 0

    # if brakes are active, reset motor_current_target
    if ebike.brakes_are_active == True:
        ebike.motor_current_target = 0

    # let's update the motor current, only if the target value changed
    if ebike.motor_current_target != ebike.previous_motor_current_target:
        ebike.previous_motor_current_target = ebike.motor_current_target
        vesc.set_motor_current_amps(ebike.motor_current_target)

async def task_read_sensors_control_motor():
    while True:
        # are breaks active and we should disable the motor?
        #check_brakes() # no brake sensor

        # motor control
        motor_control()

        # idle 20ms
        await asyncio.sleep(0.02)


import math
WHEEL_DIAMETER_M = 0.74  # diameter in meters, adjust as necessary
WHEEL_CIRCUMFERENCE_M = WHEEL_DIAMETER_M * math.pi
WHEEL_CIRCUMFERENCE_MILES = WHEEL_CIRCUMFERENCE_M * 0.000621371

async def task_calculate_speed():
    last_activation_time = None

    while True:
        # wait for the sensor to be triggered
        while not wheel_speed_sensor.value:
            await asyncio.sleep(0.01)

        if last_activation_time is not None:
            # calculate the time difference in hours
            rotation_time = time.monotonic_ns() - last_activation_time  # time in nanoseconds
            rotation_time_hours = rotation_time / (3600.0 * 10**9)  # convert from ns to hours

            # speed in mph
            speed_mph = WHEEL_CIRCUMFERENCE_MILES / rotation_time_hours
            ebike.speed = int(speed_mph)
            #print(f"Speed: {ebike.speed} mph")

        last_activation_time = time.monotonic_ns()

        # wait for the sensor to be reset before the next loop iteration
        while wheel_speed_sensor.value:
            await asyncio.sleep(0.001)


async def main():

    print("starting")

    #vesc_heartbeat_task = asyncio.create_task(task_vesc_heartbeat())
    #read_sensors_control_motor_task = asyncio.create_task(task_read_sensors_control_motor())
    #display_process_data_task = asyncio.create_task(task_display_process_data())
    #display_send_data_task = asyncio.create_task(task_display_send_data())
    #calculate_speed_task = asyncio.create_task(task_calculate_speed())

    # Start the tasks. Note that log_data_task may be disabled as a configuration
    if enable_debug_log_cvs == False:
        await asyncio.gather(
            task_vesc_heartbeat(),
            task_read_sensors_control_motor(),
            task_display_process_data(),
            task_display_send_data(),
            #task_calculate_speed(),
            )
    else:
        #log_data_task = asyncio.create_task(task_log_data())
        await asyncio.gather(
            task_vesc_heartbeat(),
            task_read_sensors_control_motor(),
            task_display_process_data(),
            task_display_send_data(),
            task_calculate_speed(),
            task_log_data(),
            )
  
    print("done main()")

asyncio.run(main())
