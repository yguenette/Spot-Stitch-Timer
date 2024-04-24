# Spot-Stitch-Timer
Spot and Stitch Timer is a module to control the Miller Multimatic 215 Welder

## The module

To help weld thin metal (20, 22 and 24 AWG) and to maintain a minimal heat affected zone, it is important to find the right combination of voltage, WFS (wire feed speed), distance and trigger "on" time to eliminate the possibility of through holes or under welding. The key is to practice on similar metal pieces on a bench in ideal conditions where experimentation is possible. The voltage and WFS are pre-determined by the welder and can be fine tuned by the user - they are dialed in. Once programmed, these values will remain constant until they are changed. The nozzle distance to object is controllable by the user and more or less repeatable. The last variable (trigger ON time) is harder to reproduce since the position, the posture and the shear number of welds can make it difficult to maintain/repeat consistently. This is where a spot timer comes in. Once programmed with a spot ON time, it will remain the same until changed by the user. Having the flexibility of adding a delay time before the spot weld ON time will allow the user to press/release the trigger, before the weld starts and have a more stable position for the weld.

The spot/stitch timer module controls the welder with very specific welding time that will help with reproducibility of the welds. By dialing in the voltage, WFS, distance and weld time, we are closer to achieving repeatable welds.

This module (Raspberry Pi Pico and a 4 channels relay board) is packaged in a 3D printed box. This box sits inside the welder - in the same compartment as the wire spool - between the trigger torch and the welder. This module has 4 mode of operations. They are:

	1.  **Unpowered-Normal** : In this mode (default) the torch's trigger is passed through to the welder.
	2.  **Powered-Normal** : In this mode (default) the torch's trigger is passed through to the welder.
	3.  **Powered-Spot** : In this mode, the torch's trigger is isolated from the welder and sensed by the spot/stitch timer module. The Spot weld-time is programmable: delay and the spot weld ON time are specified. Each time the trigger is pressed/released, the module will create a combination Delay/Spot weld ON sequence;
	4.  **Powered-Stitch** : In this mode, the torch's trigger is isolated from the welder and sensed by the spot/stitch timer module. The Stitch ON/OFF weld-time is programmable: delay and the stitch weld ON/OFF time are specified. This sequence weld-ON/weld-OFF is repeated until the trigger is pressed/released again.

## The control software (interface):

When powered, the spot/stitch timer module will default to normal mode. The module can be controlled via Bluetooth using a android smartphone. The Android program used to communicate with the spot/stitch timer module is called: Serial Bluetooth Terminal, and is available through the app store.

Once connected, there are 6 pre-program functions and 2 commands supported. 

The 6 pre-programmed functions are:

	1.  **normal** : This programs the powered module to return to normal mode;
	2.  **mode?** : This sends a command to the module asking to report the present mode of operation. The possible response is:
		a. normal;
		b. spot;
		c. stitch;
	3.  **prog?** : This sends a command to the module asking to report the programmed delay, On and Off (only for stitch mode) for both spot and stitch modes;
	4.  **temp?** : asking the raspberry pi pico for its internal temperature. Normal temperature that I have seen range from 26C to 39C. The specification for the pico is : Max = +70C, Min = -20C.
	5.  **count?** : This reports the number of spot welds performed in this session and the number of stitch welds in this session;
	6.  **help** : reports the format of the 2 additional commands. They are:
		a. Spot delay ON
		b. Stitch delay ON OFF

The 2 commands supported are:

	1. spot <delay> <ON>
	2. stitch <delay> <ON> <OFF>
	

Looking at the Serial Bluetooth Terminal application, we can connect with the module by pressing the symbol on the second line from the top, third from the left.

The spot/stitch supported commands are typed on the bottom line. The command is send by pressing the icon on the right side of that line.

![Screenshot_20240423_170638_Serial Bluetooth Terminal](https://github.com/yguenette/Spot-Stitch-Timer/assets/102556736/966b02df-fae5-4fc7-beef-712950416388)

## The final product

![20240423_174604](https://github.com/yguenette/Spot-Stitch-Timer/assets/102556736/4dfcf40d-8d10-4a2f-bb19-e2e831accd54)
