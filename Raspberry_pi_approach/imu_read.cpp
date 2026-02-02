// g++ -O2 -std=c++17 icm20948_spi.cpp -o icm
#include <linux/spi/spidev.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <chrono>

static constexpr uint8_t REG_BANK_SEL = 0x7F; // :contentReference[oaicite:20]{index=20}
static constexpr uint8_t WHO_AM_I     = 0x00; // :contentReference[oaicite:21]{index=21}
static constexpr uint8_t USER_CTRL    = 0x03; // :contentReference[oaicite:22]{index=22}
static constexpr uint8_t PWR_MGMT_1   = 0x06; // :contentReference[oaicite:23]{index=23}
static constexpr uint8_t PWR_MGMT_2   = 0x07; // :contentReference[oaicite:24]{index=24}
static constexpr uint8_t ACCEL_XOUT_H = 0x2D; // :contentReference[oaicite:25]{index=25}

static constexpr uint8_t ACCEL_SMPLRT_DIV_1 = 0x10; // bank2 :contentReference[oaicite:26]{index=26}
static constexpr uint8_t ACCEL_SMPLRT_DIV_2 = 0x11; // bank2 :contentReference[oaicite:27]{index=27}

static inline uint8_t bank_val(int bank) { return (uint8_t)((bank & 0x3) << 4); }

class Spi {
public:
    Spi(const char* dev, uint32_t hz) {
        fd_ = ::open(dev, O_RDWR);
        if (fd_ < 0) { perror("open"); std::exit(1); }

        uint8_t mode = SPI_MODE_0;
        uint8_t bits = 8;
        if (ioctl(fd_, SPI_IOC_WR_MODE, &mode) < 0) perror("SPI_IOC_WR_MODE");
        if (ioctl(fd_, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0) perror("SPI_IOC_WR_BITS_PER_WORD");
        if (ioctl(fd_, SPI_IOC_WR_MAX_SPEED_HZ, &hz) < 0) perror("SPI_IOC_WR_MAX_SPEED_HZ");
        hz_ = hz;
    }

    ~Spi() { if (fd_ >= 0) ::close(fd_); }

    void xfer(const uint8_t* tx, uint8_t* rx, size_t n) {
        spi_ioc_transfer tr{};
        tr.tx_buf = (unsigned long)tx;
        tr.rx_buf = (unsigned long)rx;
        tr.len = n;
        tr.speed_hz = hz_;
        tr.bits_per_word = 8;
        tr.cs_change = 0;
        if (ioctl(fd_, SPI_IOC_MESSAGE(1), &tr) < 0) perror("SPI_IOC_MESSAGE");
    }

private:
    int fd_{-1};
    uint32_t hz_{0};
};

struct AccelRaw { int16_t ax, ay, az; };

class Icm20948 {
public:
    Icm20948(Spi& spi) : spi_(spi) {}

    void set_bank(int bank) { write_reg_raw(REG_BANK_SEL, bank_val(bank)); }

    uint8_t read_reg_raw(uint8_t reg) {
        uint8_t tx[2] = { (uint8_t)(0x80 | (reg & 0x7F)), 0x00 };
        uint8_t rx[2] = {};
        spi_.xfer(tx, rx, 2);
        return rx[1];
    }

    void write_reg_raw(uint8_t reg, uint8_t val) {
        uint8_t tx[2] = { (uint8_t)(reg & 0x7F), val };
        uint8_t rx[2] = {};
        spi_.xfer(tx, rx, 2);
    }

    void write_reg(int bank, uint8_t reg, uint8_t val) {
        set_bank(bank);
        write_reg_raw(reg, val);
    }

    void init_spi_only() {
        set_bank(0);

        // I2C_IF_DIS bit (bit4) in USER_CTRL :contentReference[oaicite:28]{index=28}
        uint8_t uc = read_reg_raw(USER_CTRL);
        uc |= (1u << 4);
        write_reg_raw(USER_CTRL, uc);

        write_reg_raw(PWR_MGMT_1, 0x01);
        write_reg_raw(PWR_MGMT_2, 0x00);
    }

    bool check_whoami() {
        set_bank(0);
        return read_reg_raw(WHO_AM_I) == 0xEA;
    }

    void set_accel_rate_div(uint16_t div12) {
        div12 &= 0x0FFF;
        write_reg(2, ACCEL_SMPLRT_DIV_1, (div12 >> 8) & 0x0F);
        write_reg(2, ACCEL_SMPLRT_DIV_2, div12 & 0xFF);
    }

    AccelRaw read_accel_raw() {
        set_bank(0);
        uint8_t tx[1 + 6];
        uint8_t rx[1 + 6];
        tx[0] = (uint8_t)(0x80 | (ACCEL_XOUT_H & 0x7F));
        std::memset(tx + 1, 0, 6);
        std::memset(rx, 0, sizeof(rx));
        spi_.xfer(tx, rx, sizeof(tx));

        auto be16 = [&](int i)->int16_t {
            return (int16_t)((rx[i] << 8) | rx[i+1]);
        };
        return { be16(1), be16(3), be16(5) };
    }

private:
    Spi& spi_;
};

int main() {
    Spi spi("/dev/spidev0.0", 7'000'000);
    Icm20948 imu(spi);

    imu.init_spi_only();
    if (!imu.check_whoami()) {
        std::fprintf(stderr, "WHO_AM_I mismatch\n");
        return 1;
    }
    std::puts("ICM-20948 OK");

    imu.set_accel_rate_div(0);

    const double target_hz = 1000.0;
    const auto period = std::chrono::duration<double>(1.0 / target_hz);
    auto next = std::chrono::steady_clock::now();

    for (int i = 0; i < 2000; ++i) {
        while (std::chrono::steady_clock::now() < next) {}
        next += std::chrono::duration_cast<std::chrono::steady_clock::duration>(period);

        auto a = imu.read_accel_raw();
        std::printf("%d,%d,%d\n", a.ax, a.ay, a.az);
    }
    return 0;
}
