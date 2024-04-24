# Spot-Stitch-Timer
Spot and Stitch Timer module to control the Miller Multimatic 215 Welder

The spot/stitch timer module is hardware/software that controls the welder with very specific welding time that will help with reproducibility of the welds. By dialing in the voltage, WFS, distance and weld time, we are closer to achieving repeatable welds.

This module is electronic circuitry packaged in a 3D printed box. This box sits inside the welder - in the same compartment as the wire spool - between the trigger torch and the welder. This module has 4 mode of operations. They are:

	1. Unpowered-Normal: In this mode (default) the torch's trigger is passed through to the welder as it normally did.
	2. Powered-Normal: In this mode (default) the torch's trigger is passed through to the welder as it normally did.
	3. Powered-Spot: In this mode, the torch's trigger is isolated from the welder and sensed by the spot/stitch timer module. The Spot weld time control are programmable: delay in the spot mode and the spot timer ON time are specified. Each time the trigger is pressed, the module will create a combination Delay/Spot welding sequence;
	4. Powered-Stitch: In this mode, the torch's trigger is isolated from the welder and sensed by the spot/time timer module. The Stitch welder-ON/welder-OFF time control are programmable: delay in the stitch mode and the stitch timer ON/OFF time are specified. This sequence ON/OFF is repeated until the trigger is pressed again.
