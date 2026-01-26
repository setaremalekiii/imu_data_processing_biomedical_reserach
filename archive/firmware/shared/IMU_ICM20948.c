#include "IMU_ICM20948.h"

static float accel_scale_factor;
static void set_cs()
static uint8_t  read_single_icm20948_reg(userbank ub, uint8_t reg);
void icm20948_init()
// {
// 	while(!icm20948_who_am_i());

// 	icm20948_device_reset();
// 	icm20948_wakeup();

// 	icm20948_clock_source(1);
// 	icm20948_odr_align_enable();
	
// 	icm20948_spi_slave_enable();
	
// 	icm20948_gyro_low_pass_filter(0);
// 	icm20948_accel_low_pass_filter(0);

// 	icm20948_gyro_sample_rate_divider(0);
// 	icm20948_accel_sample_rate_divider(0);

// 	icm20948_gyro_calibration();
// 	icm20948_accel_calibration();

// 	icm20948_gyro_full_scale_select(_2000dps);
// 	icm20948_accel_full_scale_select(_16g);
// }

void icm20948_accel_read(axises* data)
{
	uint8_t* temp = read_multiple_icm20948_reg(ub_0, B0_ACCEL_XOUT_H, 6);

	data->x = (int16_t)(temp[0] << 8 | temp[1]);
	data->y = (int16_t)(temp[2] << 8 | temp[3]);
	data->z = (int16_t)(temp[4] << 8 | temp[5]) + accel_scale_factor; 
	// Add scale factor because calibraiton function offset gravity acceleration.
}

void icm20948_accel_read_g(axises* data)
{
	icm20948_accel_read(data);

	data->x /= accel_scale_factor;
	data->y /= accel_scale_factor;
	data->z /= accel_scale_factor;
}