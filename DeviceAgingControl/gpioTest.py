from gpiozero import LED, Button
from time import sleep

led= LED(20)
led.off()
sleep(5)
led.on()
sleep(1)
