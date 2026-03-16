#include "hw_icm42688.h"

static void activate_imu(){
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_RESET);
}

static void deactivate_imu(){
    HAL_GPIO_WritePin(IMU_CS_PORT, IMU_CS_PIN, GPIO_PIN_SET);
}

static void sel_user_bank(user_bank_t bank){
    // confirming the correct REG_BANK is selected
    uint8_t tx[2] = { (uint8_t)(REG_BANK_SEL & 0x76), (uint8_t)(bank) }; // write 0x76 then bank
    // adding rx call for testing 
    uint8_t rx[2] = {0};
    activate_imu();
    // HAL_StatusTypeDef spi_status;
    HAL_SPI_Transmit(&hspi1, tx, 2, 100);
    HAL_SPI_Receive(&hspi1, rx, 2, 100);
    deactivate_imu();
}


void imu_init(void){
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
    uint8_t temp_data;
    // setting pwr mgmt 1 to 0b11000001 auto clear and select default PLL clock
    // imu_write_reg(_b0,PWR_MGMT_1, 0xc1); //resets imu sensor
    // HAL_Delay(100); // givnig some time for imu to wake up and be ready for communication
    // 
    // imu_write_reg(_b0, PWR_MGMT_1, 0x01); // exit sleep mode 
    imu_write_reg(_b0, PWR_MGMT0, 0x40);   // 0b01000000 reset
    HAL_Delay(100);                        // 100ms is safe (often 45ms used)
    imu_write_reg(_b0, PWR_MGMT0, 0x01);   // wake 0b01000011
    imu_write_reg(_b2, ACCEL_CONFIG, ((ACCEL_RANGE_VALUE<< 1)|0x01)); // turning on the digital lowpass filter
    // 00010000 the 4th bit is enabled meaning disable I2C and enable SPI
    imu_read_reg(_b0, USER_CTRL, &temp_data); // serial interface entering spi mode
    temp_data |= 0x10;
    imu_write_reg(_b0, USER_CTRL, temp_data); 
    sel_user_bank(_b0);
}

void imu_write_reg(user_bank_t bank, uint8_t reg, uint8_t data){
    sel_user_bank(bank);
    uint8_t tx[2] = {reg, data};
    activate_imu();
    HAL_SPI_Transmit(&hspi1, tx, 2, 100);
    deactivate_imu();
}

void imu_read_reg(user_bank_t bank, uint8_t address, uint8_t *data){
    sel_user_bank(bank);
    // SPI is always full-duplex: every received bit happens at the same time as a transmitted bit. 
    // So to “receive 1 byte”, the master must still provide 8 clock pulses, which normally happens 
    // by transmitting a dummy byte (commonly 0x00 or 0xFF).
    uint8_t temp_data = 0x80 | address; // MSB 1 for read
    activate_imu();
    HAL_StatusTypeDef spi_status;
    spi_status = HAL_SPI_Transmit(&hspi1, &temp_data, 1, 100);
    // watch data variable to see if the correct value is read
    HAL_SPI_Receive(&hspi1, data, 1 , 100);
    deactivate_imu();
}


void imu_read_data(imu_data_t *data){
    uint8_t data_rx[6];
    uint8_t temp_data = 0x80|ACCEL_XOUT_H;
        sel_user_bank(_b0);

    activate_imu();
    HAL_SPI_Transmit(&hspi1, &temp_data, 1, 100);
    HAL_SPI_Receive(&hspi1, data_rx, 6, 100);
    deactivate_imu();

    // You must combine two 8-bit reads into a 16-bit signed value:
    data -> x_accel = ((uint16_t)data_rx[0] << 8) + data_rx[1];
    data -> y_accel = ((uint16_t)data_rx[2] << 8) + data_rx[3];
    data -> z_accel = ((uint16_t)data_rx[4] << 8) + data_rx[5];
}

//Helper function 
void transmit_uint8(uint16_t value) {
    char buf[10]; // "-32768\r\n" fits
    int n = snprintf(buf, sizeof(buf), "%d\r\n", (int)value);
    if (n > 0) HAL_UART_Transmit(&huart3, (uint8_t*)buf, (uint16_t)strlen(buf), 100);
  }

  // faster method of transmitting all data at once! 
void transmit_xyz(int16_t x, int16_t y, int16_t z)
{
    char buf[64];
    int n = snprintf(buf, sizeof(buf), "%d,%d,%d\n", (int)x, (int)y, (int)z);
    if (n > 0) {
        HAL_UART_Transmit(&huart3, (uint8_t*)buf, (uint16_t)n, 100);
    }
}


