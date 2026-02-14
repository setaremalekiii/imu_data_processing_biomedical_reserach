import snbus 
import time 
class mpu6050:
    G = 9.806
    addresss = None
    bus = None 

    _accel_2g = 16384.0
    
    