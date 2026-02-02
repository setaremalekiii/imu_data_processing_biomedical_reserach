#include "hw_imu.h"

static  void activate_imu(){
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_RESET);
}

static void deactivate_imu(){
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_SET);
}

static void sel_user_bank(user_bank_t bank){
    uint8_t tx[2] = { REG_BANK_SEL, (uint8_t)((bank&0x3)<<4) }; // write 0x7F then bank
    //uint8_t rx[2] = {0};
    activate_imu();
    // HAL_StatusTypeDef spi_status;
    HAL_SPI_Transmit(&IMU_SPI, tx, 2, 100);
    // HAL_SPI_Receive(&IMU_SPI, rx, 2, 100);
    deactivate_imu();
    //uint8_t who;
    // uint8_t who_am_i = rx[1];
    // spi_status  = HAL_SPI_Transmit(&IMU_SPI, &data,   1, 100);
}


void imu_init(void){
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
    uint8_t temp_data;
    imu_write_reg(_b0,PWR_MGMT_1, 0xc1);
    imu_write_reg(_b0, PWR_MGMT_1, 0x01);
    imu_write_reg(_b2,ODR_ALIGN_EN, 0x01);
    imu_write_reg(_b2,  ACCEL_SIMLRT_DIV_1,0x00);
    imu_write_reg(_b2,  ACCEL_SMPLRT_DIV_2,0x00);
    imu_write_reg(_b2, ACCEL_CONFIG, ((ACCEL_RANGE_VALUE<< 1)|0x01));    
    imu_read_reg(_b0,USER_CTRL, &temp_data);
    temp_data |= 0x10;
    imu_write_reg(_b0, USER_CTRL,temp_data);    
    sel_user_bank(_b0);
}

void imu_write_reg(user_bank_t bank, uint8_t reg, uint8_t data){
    sel_user_bank(bank);
    // uint8_t tx[2] = {reg, data};
    // activate_imu();
    // HAL_StatusTypeDef spi_status;
    // spi_status = HAL_SPI_Transmit(&IMU_SPI, tx, 2, 100);
    // deactivate_imu();
    //spi_status = HAL_SPI_Transmit(&IMU_SPI, &data, 1, 100);
        //sel_user_bank(bank);
    uint8_t tx[2] = { (uint8_t)(reg & 0x7F), data }; // MSB=0 for write
    activate_imu();
    HAL_SPI_Transmit(&IMU_SPI, tx, 2, 100);
    deactivate_imu();

}

void imu_read_reg(user_bank_t bank, uint8_t address, uint8_t *data){
    sel_user_bank(bank);
    uint8_t temp_data = 0x80 | address; // MSB 1 for read
    uint8_t tx[2] = { (uint8_t)(0x80 | (address & 0x7F)), 0x00 };
    uint8_t rx[2] = {0};
    activate_imu();
    HAL_StatusTypeDef spi_status;
    spi_status = HAL_SPI_TransmitReceive(&IMU_SPI, tx, rx, 2, 100);
    deactivate_imu();
    *data = rx[1];

}


void imu_read_data(imu_data_t *data){
//   uint8_t tx2[2] = { 0x7f , 0x00};  // WHO_AM_I (0x00) + READ bit, dummy
//   uint8_t rx2[2] = { 0 };

//   activate_imu();
//   HAL_SPI_TransmitReceive(&IMU_SPI, tx2, rx2, 2, 1000);
//   deactivate_imu();

//   uint8_t who_am_i = rx2[1];   // THIS is the WHO_AM_I value
//     HAL_Delay(1000);
    // uint8_t data_rx[12];
    // uint8_t temp_data = 0x80|ACCEL_XOUT_H;
    // activate_imu();
    // HAL_SPI_Transmit(&IMU_SPI, &temp_data, 1, 100);
    // HAL_SPI_Receive(&IMU_SPI, data_rx, 12, 100);
    // data -> x_accel = ((uint16_t)data_rx[0] << 8) | data_rx[1];
    // data -> y_accel = ((uint16_t)data_rx[2] << 8) | data_rx[3];
    // data -> z_accel = ((uint16_t)data_rx[4] << 8) | data_rx[5];
    // deactivate_imu();
    sel_user_bank(_b0);
    HAL_Delay(10);
    uint8_t tx[1 + 6] = { (uint8_t)(0x80 | ACCEL_XOUT_H), 0,0,0,0,0,0 };
    uint8_t rx[1 + 6] = {0};

    activate_imu();
    HAL_SPI_TransmitReceive(&IMU_SPI, tx, rx, sizeof(tx), 100);
    deactivate_imu();

    // rx[0] is dummy (during address phase). Data starts at rx[1].
    data->x_accel = (int16_t)((rx[1] << 8) | rx[2]);
    data->y_accel = (int16_t)((rx[3] << 8) | rx[4]);
    data->z_accel = (int16_t)((rx[5] << 8) | rx[6]);

}

// You must combine two 8-bit reads into a 16-bit signed value:

// int16_t raw = (high_byte << 8) | low_byte;
