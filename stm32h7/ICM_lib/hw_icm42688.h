#ifndef HW_ICM42688_H_
#define HW_ICM42688_H_
#include <stdint.h>
#include <main.h>
#include "stdio.h"

typedef struct{
    int16_t x_accel; 
    int16_t y_accel;
    int16_t z_accel;   
} imu_data_t;

extern SPI_HandleTypeDef hspi1;
extern UART_HandleTypeDef huart3;
#define ACCEL_RANGE_VALUE ((accel_range_t) _accel_2g)
#define IMU_CS_PORT GPIOD
#define IMU_CS_PIN  GPIO_PIN_14
#define REG_BANK_SEL 0x76
#define WHO_AM_I 0x75
#define PWR_MGMT0 0x4E
#define ACCEL_CONFIG0 0x50
#define FSYNC_CONFIG 0x62 // contains all flags 
#define ACCEL_DATA_X1 0x1F // Upper byte of Accel X-axis data
#define ACCEL_DATA_X0 0x20 // Lower byte of Accel X-axis data
#define ACCEL_DATA_Y1 0x21
#define ACCEL_DATA_Y0 0x22
#define ACCEL_DATA_Z1 0x23
#define ACCEL_DATA_Z0 0x24

typedef enum{
    _accel_2g ,
    _accel_4g,
    _accel_8g,
    _accel_16g
} accel_range_t;

typedef enum {
    _b0 = 0,
    _b1 = 1<<4,
    _b2 = 2<<4,
    _b3 = 3<<4,
}user_bank_t;

void imu_init();
void imu_write_reg(user_bank_t bank, uint8_t reg, uint8_t data);
void imu_read_reg(user_bank_t bank, uint8_t address, uint8_t *data);
void imu_read_data(imu_data_t *data);
void transmit_uint8(uint16_t value);
void transmit_xyz(int16_t x, int16_t y, int16_t z);
#endif //HW_IMU_H_
