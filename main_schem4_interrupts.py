#-------------------
# YAG:
#
# Code to start and monitor the Bluetooth LE (BT) function and monitor the welder trigger.
#   At the time of this writing (March 2024), the dual core functionality was
#   attempted but not successful while using BT. It was however dual core was functional while using simple
#   functions like LED blinking and counter exercises.
#
# All programs are modified via the BT interface. The Android application that I used is called:
#
#   Serial Bluetooth Terminal
#
#
# The steps in this program are:
#
#	1) Initialize the relays so that the circuit operates in "Normal" mode by default;
#       To be clear, after further investigation of bouncing with the Miller torch
#       - pressing the trigger causes between 11 and 15 bounces with a duration of worst case,
#       seen of 235ms (with 4.7kOhms pull-down), while the release of the trigger causes very
#       little bounces at all.
#       In the 'normal' mode, I decided to bypass the controller altogether and passthru the
#       miller trigger directly to the welder. Note that the welder likely has (internally)
#       a debouncing circuit. In this mode the relays are all in their OFF position.
#	2) When the trigger is activated, the program will determine if the mode of operation is:
#		a) NORMAL - trigger passthru directly to welder;
#		b) SPOT - trigger on/off is determined by the spot welder programmed duration;
#		c) STITCH - trigger on/off is determined by the stitch programmed ON time followed by
#			the programmed OFF time - repeat as long as the trigger remains ON.
#
# If the microcontroller is un-powered, the relays will be positioned to allow the trigger to
#   be passed on to the welder.
#
# 1.0.0 - Initial version. March 26, 2024
#			- Allow bluetooth communication
#
# 5.0.0 - Now using V3 of the schematic - see green book for more details.
#       - Two (2) major changes done to the schematic:
#           - 1) Relay 3 was simplified so that Common pole and NO (Normally Open) pole are
#                  connected to the outputs of the relay 1 and 2 (Normally Closed poles).
#
#           - 2) Relay 4 is now used to disconnected the 'white' trigger wire from the pin 4 of
#                  the RPI-PICO. When the RPI-PICO is un-powered, the voltage at that pin is 17.7V
#                  That has the potential to destroy the PICO.
#
# 6.0.0 - Now using version 4 of the schematic. In this version, the "pwr_3v3_meas" pin is now connected
#         to the 3V3 power pin (3.3V). This means that wire on pin 4 is moved to pin 36.
#         Also, pin 34 is now jumpered to GND (pin 38).
#         From a programming point of view, these 2 pins (GPIO28 (pin 34) and GPIO2 (pin 4)) are now
#         GPIO input pins.

#
# future work:
#
#-------------------------------
# Import necessary modules
import _thread, utime
from machine import Pin, mem32
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral

bounce_delay = 0.1
relay_switching = 0.1

# Backend GPIO pin definitions
# --------------------------------
relay_1 = machine.Pin(7,machine.Pin.OUT) #Relay 1 control. Turn ON by forcing 0V.
relay_2 = machine.Pin(8,machine.Pin.OUT) #Relay 1 control. Turn ON by forcing 0V.
relay_3 = machine.Pin(9,machine.Pin.OUT) #Relay 1 control. Turn ON by forcing 0V.
relay_4 = machine.Pin(10,machine.Pin.OUT) #Relay 1 control. Turn ON by forcing 0V.

# Relay control section (initializtion/default settings). Backend:
#------------------------------------------------------------------
# Control the GPIO pins to the correct default states
led_state = 0 # PICO green LED. Default state is OFF
relay_1_state = 0 # Relay 1 control state. Default is OFF - used for the passthru of the white wire
relay_2_state = 0 # Relay 2 control state. Default is OFF - used for the passthru of the black wire
relay_3_state = 0 # Relay 3 control state. Default is OFF - this relay is only controlled during SPOT and STITCH modes.
relay_4_state = 0 # Relay 4 control state. Default is OFF

relay_1.value(not relay_1_state)
relay_2.value(not relay_2_state)
relay_3.value(not relay_3_state)
relay_4.value(not relay_4_state)

utime.sleep(relay_switching) # Wait for the relays to settle.

# Frontend GPIO pins to use for the switch sensing
#---------------------------------------------------------
#This output is used to drive a fixed level. Between this output (pwr_3v3_meas) and the sensing input (sw_in), there is relay4 (default off)
#   and the trigger of the welder.
# pwr_3v3_meas = machine.Pin(2,  machine.Pin.IN) #This is now connected to 3.3V
sw_in    = machine.Pin(6,  machine.Pin.IN) #other side of the switch. Input. Pull-up of 4.7K provided externally. The other side of this PD is another GPIO (28)
# gnd_meas = machine.Pin(28, machine.Pin.IN) # GPIO pin used as a GND when in SPOT and STITCH modes only. Else input floating,
sw_in.irq(handler=None)  # disable interrupt during the switching of relay4. It creates an interrupt.

# Temperature sensor initialization
#------------------------------------------
adcpin = 4
sensor = machine.ADC(adcpin)


#Global variables:
normal = 1
spot = 0
spot_delay = 0
spot_time = 0
stitch = 0
stitch_delay = 0
stitch_ON = 0
stitch_OFF = 0
interrupt_flag = 0
spot_counter = 0
stitch_counter = 0

# Bluetooth Inititalization:
#----------------------------------------
# Create a Bluetooth Low Energy (BLE) object
ble = bluetooth.BLE()

# Create an instance of the BLESimplePeripheral class with the BLE object
sp = BLESimplePeripheral(ble)


# GPIO output drive coding:
#------------------------------------
PADS_BANK0_BASE     = 0x4001C000

PAD_GPIO            = PADS_BANK0_BASE + 0x04 # Add (pin * 4)
PAD_GPIO_MPY        = 4

PAD_DRIVE_BITS      = 4 # 0=2mA, 1=4mA, 2=8mA, 3=12mA   Default=1, 4mA drive

def SetPinDriveStrength(pin, mA):
  adr = PAD_GPIO + PAD_GPIO_MPY * pin
  mem32[adr] &= 0xFFFFFFFF ^ ( 0b11 << PAD_DRIVE_BITS)
  if   mA <= 2 : mem32[adr] |= 0b00 << PAD_DRIVE_BITS
  elif mA <= 4 : mem32[adr] |= 0b01 << PAD_DRIVE_BITS
  elif mA <= 8 : mem32[adr] |= 0b10 << PAD_DRIVE_BITS
  else         : mem32[adr] |= 0b11 << PAD_DRIVE_BITS


#This is code that will support interruptions for the sw_in pin.
#----------------------------------------------------------------
def callback(pin):
    global normal
    global spot
    global stitch
    global interrupt_flag
    
    # We should never see a trigger in this mode - mainly because relay4 is open which means there is no contact between GPIO input and output.
    if spot == 1:
        interrupt_flag = 1 # used most often
    elif stitch == 1:
        interrupt_flag = 1 # used most often
    else: # only normal remaining - which should never happen because relay4 is open...
        interrupt_flag = 0


# This is the code to handle the different modes once a trigger is detected
# -------------------------------------------------------------------------
def trigger():
#     import utime
    global normal
    global spot
    global spot_delay
    global spot_time
    global stitch
    global stitch_delay
    global stitch_ON
    global stitch_OFF
    global relay_1_state
    global relay_2_state
    global relay_3_state
    global relay_4_state
    global interrupt_flag
    global spot_counter
    global stitch_counter
    global relay_switching
#
    # NORMAL Section
    #---------------
    if normal == 1:      # ...and the mode is normal. Trigger ON/OFF programs welder ON/OFF.
        # should not happen because relay4 is open and this means that the pwr_3v3_meas cannot drive a level 1 through the trigger.
        sp.send('YAG_ERROR: No Trigger in NORMAL mode\r\n')
        

    # SPOT TIMER SECTION
    #-------------------
    elif spot == 1:
        
        # Wait a finite amount of time for the trigger to be released
        # to make the welding more comfortable.
        #------------------------------------------------------------
        utime.sleep(spot_delay)
        spot_counter = spot_counter + 1
        
        # control the relay to simulate the trigger being pressed:
        #---------------------------------------------------------
        relay_3_state = 1
        relay_3.value(not relay_3_state) # turn relay 3 ON
        # wait for switching
        utime.sleep(relay_switching)  # Wait relay_switching before continuing.

        utime.sleep(spot_time) # wait the specified anmount of time with simulated trigger pressed.
        
        # control the relay to simulate the trigger being released:
        #----------------------------------------------------------
        relay_3_state = 0
        relay_3.value(not relay_3_state) # turn relay 3-4 OFF (open these 2 relays)
        # wait for switching
        utime.sleep(relay_switching)  # Wait relay_switching before continuing.
        
        # This is to cover the case where the trigger remains pressed....wait until it is
        #   released
        #--------------------------------------------------------------------------------
        while (sw_in.value() == 1): # trigger is still on.
            # do nothing. Wait it out until trigger is released. No other trigger will start a spot weld.
            pass
        utime.sleep(bounce_delay) # it will come out the 'while' only if the trigger was released.
        interrupt_flag = 0 # reset interrupt flag manually....
        
        
    elif stitch == 1:
        # Wait a finite amount of time for the trigger to be released
        # to make the welding more comfortable.
        #------------------------------------------------------------
        
        utime.sleep(stitch_delay)
        
        # first cycle run manually. This eliminates the need to account for any bouncing in the trigger.
        # At the end of this time, the trigger will have been stable - either ON or OFF.
        stitch_counter = stitch_counter + 1
        relay_3_state = 1
        relay_3.value(not relay_3_state) # turn relay 3 ON (close this relay)

        utime.sleep(relay_switching)  # Wait relay_switching before continuing.

        utime.sleep(stitch_ON) # wait the specified amount of time with the trigger ON
                
        interrupt_flag = 0 #reset this flag

        # control the relay to simulate the trigger being released:
        #----------------------------------------------------------
        relay_3_state = 0
        relay_3.value(not relay_3_state) # turn relay 3-4 OFF (open these 2 relays)

        utime.sleep(relay_switching)  # Wait relay_switching before continuing.
        
        # wait the amount of time for the trigger being released.
        utime.sleep(stitch_OFF)
        
        
        # dtermine the state of the trigger based on the level at the sw_in pin.
        #----------------------------------------------------------------------
        if (sw_in.value() == 1): # this means that the trigger is still on and the looping will continue until it is released.
                                # This is the case where the user wants to work in the mode where only one ON/OFF is used
                                # for the duration of thestitch mode.
                                
            # control the relay to simulate the trigger STILL being pressed:
            #---------------------------------------------------------------
            while (sw_in.value() == 1): # while the trigger is ON continue to ON/OFF the welder until released
                stitch_counter = stitch_counter + 1
                relay_3_state = 1
                relay_3.value(not relay_3_state) # turn relay 3-4 ON (close these 2 relays)

                utime.sleep(relay_switching)  # Wait relay_switching before continuing.

                utime.sleep(stitch_ON) # wait the specified amount of time with the trigger ON
                        
                # control the relay to simulate the trigger being released:
                #----------------------------------------------------------
                relay_3_state = 0
                relay_3.value(not relay_3_state) # turn relay 3-4 OFF (open these 2 relays)

                utime.sleep(relay_switching)  # Wait relay_switching before continuing.

                # wait the amount of time for the trigger being released.
                utime.sleep(stitch_OFF)
        
        elif (sw_in.value() == 0): # this means that the trigger was released in the first stitch cycle and to stop the cycles
                                    # from continuing, we need another trigger ON action to stop it.
            # control the relay to simulate the trigger was released previously:
            #---------------------------------------------------------------------
            while (interrupt_flag == 0): # repeat this loop until another interrupt is generated.
                stitch_counter = stitch_counter + 1
                relay_3_state = 1
                relay_3.value(not relay_3_state) # turn relay 3-4 ON (close these 2 relays)

                utime.sleep(relay_switching)  # Wait relay_switching before continuing.

                utime.sleep(stitch_ON) # wait the specified amount of time with the trigger ON
                        
                # control the relay to simulate the trigger being released:
                #----------------------------------------------------------
                relay_3_state = 0
                relay_3.value(not relay_3_state) # turn relay 3-4 OFF (open these 2 relays)

                utime.sleep(relay_switching)  # Wait relay_switching before continuing.

                # wait the amount of time for the trigger being released.
                utime.sleep(stitch_OFF)

        interrupt_flag = 0
        

def ReadTemperature():
 	adc_value = sensor.read_u16()
 	volt = (3.3/65535) * adc_value
 	temperature = 27 - (volt - 0.706)/0.001721
 	return round(temperature, 1)

def default_normal():
    # disable interrupt requests.
    
    relay_1_state = 0 # Relay 1 control state. Default is OFF - used for the passthru of the white wire
    relay_2_state = 0 # Relay 2 control state. Default is OFF - used for the passthru of the black wire
    relay_3_state = 0 # Relay 3 control state. Default is OFF - this relay is only controlled during SPOT and STITCH modes.
    relay_4_state = 0 # Relay 4 control state. Default is OFF

    # no interrupt needed for normal mode. Signal passthrough spot timer box.
    sw_in.irq(handler=None)  # disable interrupt during the switching of relay4. It creates an interrupt.

    relay_4.value(not relay_4_state) # turn off relay4 first to save the PICO input.
    relay_3.value(not relay_3_state)
    
    utime.sleep(relay_switching) # Wait for the relays to settle.
    
    relay_1.value(not relay_1_state)
    relay_2.value(not relay_2_state)

    utime.sleep(relay_switching) # Wait for the relays to settle.


def default_spot_stitch():
    # disable interrupt requests while switching around the relays configurations.
    
    relay_1_state = 1 # Relay 1 control state. Default is OFF - used for the passthru of the white wire
    relay_2_state = 1 # Relay 2 control state. Default is OFF - used for the passthru of the black wire
    relay_3_state = 0 # Relay 3 control state. Default is OFF - this relay is only controlled during SPOT and STITCH modes.
    relay_4_state = 1 # Relay 4 control state. Default is OFF

    relay_1.value(not relay_1_state)
    relay_2.value(not relay_2_state)
    relay_3.value(not relay_3_state)

    utime.sleep(relay_switching) # Wait for the relays to settle.
    
    sw_in.irq(handler=None)  # disable interrupt during the switching of relay4. It creates an interrupt.
    
    relay_4.value(not relay_4_state)

    utime.sleep(1) # Wait for the relays to settle.
    
    sw_in.irq(trigger=Pin.IRQ_RISING, handler=callback)

    
    
# Define a callback function to handle received data
def on_rx(data):
    global normal
    global spot
    global spot_delay
    global spot_time
    global stitch
    global stitch_delay
    global stitch_ON
    global stitch_OFF
    global led_state  # Access the global variable led_state
    global spot_counter
    global stitch_counter
    
#     print("Data received: ", data)  # Print the received data
    s_data = data.decode('ascii')
    s_data = s_data.replace("\r\n","")
#     print("String Data received: ", s_data)  # Print the received data
    if data == b'normal\r\n':
        normal = 1
        spot = 0
        stitch = 0
        
        # disable irq in this mode.
        default_normal()
        
    elif (s_data.find('spot ')!=-1):
        #
        x = s_data.split(" ")
        tmp_delay = (x[1])
        tmp = (x[2])
        
        normal = 0
        spot = 1
        spot_delay = float(tmp_delay)
        spot_time = float(tmp)
        stitch = 0
        default_spot_stitch()


    elif (s_data.find('stitch ')!=-1):
        #
        x = s_data.split(" ")
        tmp_delay_stitch = (x[1])
        tmp1 = (x[2])
        tmp2 = (x[3])
        
        normal = 0
        spot = 0
        stitch = 1
        stitch_delay = float(tmp_delay_stitch)
        stitch_ON = float(tmp1)
        stitch_OFF = float(tmp2)
        default_spot_stitch()

    elif (s_data.find('mode?') != -1): # match
        if normal == 1:
            sp.send('normal\r\n')
        
        elif spot == 1:
            sp.send('spot\r\n')
            
        elif stitch == 1:
            sp.send('stitch\r\n')
        
    elif (s_data.find('program?') != -1): # match
        data_new = 'spot delay: '+ str(spot_delay) + ', ON: ' + str(spot_time) + '\r\n'
        sp.send(data_new)
        data_new = 'stitch delay: '+ str(stitch_delay) + ', ON: ' + str(stitch_ON)+ ', OFF: ' + str(stitch_OFF) + '\r\n'
        sp.send(data_new)
        
    elif (s_data.find('temp?') != -1):
        temperature = str(ReadTemperature()) + '\r\n'
        sp.send(temperature)
        
    elif (s_data.find('counters?') != -1):
        data_new = 'spot counter: '+ str(spot_counter) + ', stitch counter: ' + str(stitch_counter) + '\r\n'
        sp.send(data_new)

    elif (s_data.find('help') != -1):
        data_new = 'spot <delay> <ON time>' + '\r\n'
        sp.send(data_new)
        data_new = 'stitch <delay> <ON time> <OFF time>' + '\r\n'
        sp.send(data_new)

    else:
        sp.send('YAG_ERROR: wrong command\r\n')
        



while True:
    if sp.is_connected():  # Check if a BLE connection is established
        sp.on_write(on_rx)  # Set the callback function for data reception

    if (interrupt_flag == 1 and normal == 0):   # trigger is pressed
        trigger()
        
#     if (sw_in.value() == 1 and normal == 0):   # trigger is pressed
#         trigger()

