# Quick test script

import time, board 
import adafruit_icm20948


# Setting up the file and board environments
i2c = board.I2C
icm = adafruit_icm20x.adafruit_icm20948(i2c)

while True:
    printf("acceleration {icm.acceleration}")
    printf("gyro{icm.gyro}")
    time.sleep(0.1)

