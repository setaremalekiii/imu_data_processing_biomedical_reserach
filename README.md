# IBL sensor reading and processing
A repository for all software and firmware for my research project. 

## Table of Contents
firmware -> containing the stm32 code, shared libraries for data transfer 

data_processing -> Laplace transform and processing it to form the outputs of frequency and amplitude from an IMU sensor 

data -> the output data from the processing 

## Tools 
- STM32h7 nucleo board 
- ICM20948 IMU sensor 



## How the sensor works

first read WHO_AM_I = 0xEA from address 0x00 in User Bank 0 on the ICM-20948.
if you read 0x00, that almost always means the IMU is not actually driving MISO. check: wrong mode/wiring/CS/voltage

Ensure that the gpio cs pin is SET in MX_GPIO_Init() or eles you'll need to do a software reset for anything to work  