#ifndef HW_IMU_H_
#define HW_IMU_H_

#include <stdint.h>
#include <main.h>
#include "stdio.h"


typedef struct{
    int16_t x_accel; 
    int16_t y_accel;
    int16_t z_accel;   
} imu_data_t;

extern SPI_HandleTypeDef hspi1;
#define IMU_CS_PORT GPIOA
#define IMU_CS_PIN  GPIO_PIN_4
#define ACCEL_RANGE_VALUE _accel_2g

#define REG_BANK_SEL 0x7F
#define ODR_ALIGN_EN 0x09
#define WHO_AM_I 0
#define PWR_MGMT_1 0x06
#define USER_CTRL 0x03
#define ACCEL_SIMLRT_DIV_1 0x10
#define ACCEL_SMPLRT_DIV_2 0x10
#define ACCEL_CONFIG 0x14 
#define ACCEL_XOUT_H 0x2D
#define ACCEL_XOUT_L 0x2E
#define ACCEL_YOUT_H 0x2F
#define ACCEL_YOUT_L 0x30
#define ACCEL_ZOUT_H 0x31
#define ACCEL_ZOUT_L 0x32

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
#endif //HW_IMU_H_
