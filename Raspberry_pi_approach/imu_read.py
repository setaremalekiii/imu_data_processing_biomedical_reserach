import spidev 
import time
import csv

REG_BANK_SEK = 0x7F
WHO_AM_I = 0x00
USER_CTRL = 0x03
PWR_MGMT_1 = 0x06
PWR_MGMT_2 = 0x07

ACCEL_XOUT_H = 0x2D
ACCEL_SMPLRT_DIV_1 = 0x10
ACCEL_SMPLRT_DIV_2 = 0x11
ACCEL_CONFIG = 0x14

def bank_val(bank):
    return (bank &0x3) << 4

class ICM20948_SPI:
    def __init__(self, bus=0, device=0, hz = 7_000_000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.mode = 0
        self.spi.max_speed_hz = hz
        self.current_bank = None
        self.spi.bits_per_word = 8
        
        try: 
            self.sou.lsbfirst = False 
        except Exception: 
            pass 
        self.set_bank(0)
    
    def close(self):
        self.spi.close()
    
    def xfer(self, output):
        return self.spi.xfer2(output)
    
    def set_bank(self, bank):
        self.wrrite_reg(REG_BANK_SEK, bank_val(bank))
    
    def read_reg_raw(self, reg):
        resp = self.xfer([0x80 | (reg & 0x7F), 0x00])
        resp = resp[1]
        return resp
    
    
    def write_reg_raw(self, reg: int, val: int):
        self.xfer([reg & 0x7F, val & 0xFF])

    def read_bytes(self, start_reg: int, n: int) -> bytes:
        # Burst read: send address then clock out n bytes
        resp = self.xfer([0x80 | (start_reg & 0x7F)] + [0x00] * n)
        return bytes(resp[1:])

    def read_reg(self, bank: int, reg: int) -> int:
        self.set_bank(bank)
        return self.read_reg_raw(reg)

    def write_reg(self, bank: int, reg: int, val: int):
        self.set_bank(bank)
        self.write_reg_raw(reg, val)

    def init_spi_only(self):
        # Disable I2C interface: set I2C_IF_DIS (bit 4) in USER_CTRL  :contentReference[oaicite:17]{index=17}
        self.set_bank(0)
        uc = self.read_reg_raw(USER_CTRL)
        uc |= (1 << 4)
        self.write_reg_raw(USER_CTRL, uc)

        # Wake device: clear sleep (you can refine clock source later)
        # PWR_MGMT_1 exists at 0x06 (bank0)  :contentReference[oaicite:18]{index=18}
        self.write_reg_raw(PWR_MGMT_1, 0x01)  # common: auto clock select, sleep=0
        self.write_reg_raw(PWR_MGMT_2, 0x00)  # enable accel+gyro

    def set_accel_rate_div(self, div12: int):
        # div12 is 12-bit across DIV_1 (high nibble) and DIV_2 (low byte)
        div12 &= 0x0FFF
        self.write_reg(2, ACCEL_SMPLRT_DIV_1, (div12 >> 8) & 0x0F)
        self.write_reg(2, ACCEL_SMPLRT_DIV_2, div12 & 0xFF)

    def read_accel_raw(self):
        self.set_bank(0)
        b = self.read_bytes(ACCEL_XOUT_H, 6)  # XH,XL,YH,YL,ZH,ZL  :contentReference[oaicite:19]{index=19}
        ax = int.from_bytes(b[0:2], byteorder="big", signed=True)
        ay = int.from_bytes(b[2:4], byteorder="big", signed=True)
        az = int.from_bytes(b[4:6], byteorder="big", signed=True)
        return ax, ay, az

def main():
    imu = ICM20948_SPI(bus=0, dev=0, hz=7_000_000)
    imu.init_spi_only()

    who = imu.read_reg(0, WHO_AM_I)
    if who != 0xEA:
        print(f"WHO_AM_I mismatch: 0x{who:02X} (expected 0xEA)")
        imu.close()
        return
    print("ICM-20948 detected (WHO_AM_I = 0xEA)")

    # For ~1kHz accel, you can usually leave ODR high and just sample at 1kHz in software.
    # If you want a divider: try 0 (max internal rate) then sample at 1kHz loop rate.
    imu.set_accel_rate_div(0)

    target_hz = 1000.0
    dt = 1.0 / target_hz

    with open("accel_1khz.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_ns", "ax_raw", "ay_raw", "az_raw"])

        next_t = time.perf_counter()
        for _ in range(10_000):  # ~10 seconds
            now = time.perf_counter()
            if now < next_t:
                # Busy-wait gives tighter timing than sleep() for 1kHz
                continue
            next_t += dt

            t_ns = time.time_ns()
            ax, ay, az = imu.read_accel_raw()
            w.writerow([t_ns, ax, ay, az])

    imu.close()
    print("Wrote accel_1khz.csv")

if __name__ == "__main__":
    main()
