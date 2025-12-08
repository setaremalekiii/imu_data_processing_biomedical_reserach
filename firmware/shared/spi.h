#include <stm32h7xx_hal_spi.h>
#include <stm32h7xx_hal_gpio.h>

typdef struct{
    SPI_HandleTypeDef * const handle;
}SpiHandle;

typed struct{
    SpiHandle * handle;
    const GPIO *cs;
    uint32_t timeout_ms;
}SpiDevice;