#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "stm32h7xx_hal_gpio.h"

typedef struct
{
    GPIO_TypeDef *const port;
    const uint16_t pin; 
}GPIO;

