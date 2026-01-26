#include <stm32h7xx_hal_spi.h>
#include <stm32h7xx_hal_gpio.h>
#include "gpio.h"
#icnlude "stdbool.h"

typdef struct{
    SPI_HandleTypeDef * const handle;
}SpiHandle;

typed struct{
    SpiHandle * handle;
    const GPIO *cs;
    uint32_t timeout_ms;
}SpiDevice;

/**
 * Transmit to and receive from data FROM the device (ex: IMU) connected to the given SPI (ex:STM's spi)
 * interface.
 * @param device Peripheral: IMU 
 * @param tx_buffer A pointer to the data buffer containing the data transmitted TO the device
 * which is why its const since we will not be modifying
 * @param tx_buffer_size The size of the tx_data buffer.
 * @param rx_buffer A pointer to the data buffer that stores the data received
 * from the device connected to the SPI interface like an IMU this is why its not a const 
 * because we will be writing to this buffer
 * @param rx_buffer_size The number data received from the device connected to
 * the SPI interface.
 * @return True if data is transmitted and received successfully. Else return
 * false.
 */
bool spi_fullDuplex(const SpiDevice * device, const uint8_t *tx_buffer, uint16_t tx_buffer_size, uint8_t *rx_buffer, uint16_t rx_buffer_size);
bool spi_transmit(const SpiDevice * device, const uint8_t *tx_buffer, uint16_t tx_buffer_size);
bool spi_recieve(const SpiDevice * device, uint8_t *rx_buffer, uint16_t rx_buffer_size);