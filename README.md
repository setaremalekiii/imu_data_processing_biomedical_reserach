# IMU sensor reading and processing
A repository for all software and firmware for my research project. 

## Table of Contents
firmware -> containing the stm32 code, shared libraries for data transfer 

data_processing -> Laplace transform and processing it to form the outputs of frequency and amplitude from an IMU sensor 

data -> the output data from the processing 

## Tools 
- STM32h7 nucleo board 
- ICM20948 IMU sensor 
- STMcubemx
Please refer to this schematic for the pin connection of the STM32h723zg
https://www.st.com/resource/en/schematic_pack/mb1364-h723zg-e01_schematic.pdf 


## How the sensor works

first read WHO_AM_I = 0xEA from address 0x00 in User Bank 0 on the ICM-20948.
if you read 0x00, that almost always means the IMU is not actually driving MISO. check: wrong mode/wiring/CS/voltage

Ensure that the gpio cs pin is SET in MX_GPIO_Init() or eles you'll need to do a software reset for anything to work  


## Architecture

STM32  will read data using interupt based SPI communication at a high frequency

DMA and circular buffers will be used to store the data and write it to the serial port using UART -> this way the CPU is not occupied for writing data to the serial port. 

Once the data is written to the serial port, another python script will be ran which will be listening to the serial port on the same COM and baud   rate to record the sensor readings and write them to a csv file. 

The csv file is then analyzed to create meaningful plots.
