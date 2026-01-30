#include "hw_imu.h"

static  void activate_imu(){
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_RESET);
}

static void deactivate_imu(){
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_SET);
}

static void sel_user_bank(user_bank_t bank){
    uint8_t data = bank;
    uint8_t reg = REG_BANK_SEL; 
    activate_imu();
    HAL_StatusTypeDef spi_status;
    spi_status = HAL_SPI_Transmit(&IMU_SPI, &reg,   1, 100);
    spi_status  = HAL_SPI_Transmit(&IMU_SPI, &data,   1, 100);
    deactivate_imu();
}


void imu_init(void){
    uint8_t temp_data;
    imu_write_reg(_b0,PWR_MGMT_1, 0xc1);
    imu_write_reg(_b0, PWR_MGMT_1, 0x01);
    imu_write_reg(_b2,ODR_ALIGN_EN, 0x01);
    imu_write_reg(_b2,  ACCEL_SIMLRT_DIV_1,0x00);
    imu_write_reg(_b2,  ACCEL_SMPLRT_DIV_2,0x00);
    imu_write_reg(_b2, ACCEL_CONFIG, ((ACCEL_RANGE_VALUE<< 1)|0x01));    
    imu_read_reg(_b0,USER_CTRL, &temp_data);
    temp_data |= 0x10;
    imu_write_reg(_b2, USER_CTRL,temp_data);    
    sel_user_bank(_b0);
}

void imu_write_reg(user_bank_t bank, uint8_t reg, uint8_t data){
    sel_user_bank(bank);
    activate_imu();
    HAL_StatusTypeDef spi_status;
    spi_status = HAL_SPI_Transmit(&IMU_SPI, &reg, 1, 100);
    spi_status = HAL_SPI_Receive(&IMU_SPI, &data, 1, 100);
}

void imu_read_reg(user_bank_t bank, uint8_t address, uint8_t *data){
    uint8_t temp_data = 0x80 | address; // MSB 1 for read
    sel_user_bank(bank);
    activate_imu();
    HAL_StatusTypeDef spi_status;
    spi_status = HAL_SPI_Transmit(&IMU_SPI, &temp_data, 1, 100);
    spi_status = HAL_SPI_Receive(&IMU_SPI, data, 1, 100);
    deactivate_imu();
}


void imu_read_data(imu_data_t *data){
    uint8_t data_rx[12];
    uint8_t temp_data = 0x80|ACCEL_XOUT_H;
    activate_imu();
    HAL_SPI_Transmit(&IMU_SPI, &temp_data, 1, 100);
    HAL_SPI_Receive(&IMU_SPI, data_rx, 12, 100);
    data -> x_accel = ((uint16_t)data_rx[0] << 8) | data_rx[1];
    data -> y_accel = ((uint16_t)data_rx[2] << 8) | data_rx[3];
    data -> z_accel = ((uint16_t)data_rx[4] << 8) | data_rx[5];
    deactivate_imu();
}

// You must combine two 8-bit reads into a 16-bit signed value:

// int16_t raw = (high_byte << 8) | low_byte;
