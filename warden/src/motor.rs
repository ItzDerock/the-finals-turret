use embassy_stm32::{
    gpio::{AnyPin, Level, Output, Speed},
    mode::Async,
    usart::{BufferedUart, Error, Uart},
};
use embedded_io::{Read, Write};

pub struct Motor<'d> {
    uart: &'d mut Uart<'d, Async>,
    uart_address: u8,
    step_pin: Output<'d>,
    dir_pin: Output<'d>,
    enable_pin: Output<'d>,
}

impl<'d> Motor<'d> {
    pub fn new(
        uart: &'d mut Uart<'d, Async>,
        uart_address: u8,
        step_pin: AnyPin,
        dir_pin: AnyPin,
        enable_pin: AnyPin,
    ) -> Motor<'d> {
        let step_pin = Output::new(step_pin, Level::High, Speed::VeryHigh);
        let dir_pin = Output::new(dir_pin, Level::High, Speed::VeryHigh);
        let mut enable_pin = Output::new(enable_pin, Level::High, Speed::VeryHigh);

        // configure the registers
        let mut gconf = tmc2209::reg::GCONF::default();
        gconf.set_pdn_disable(true);

        let vactual = tmc2209::reg::VACTUAL::ENABLED_STOPPED;

        let mut ihold_irun = tmc2209::reg::IHOLD_IRUN::default();
        ihold_irun.set_ihold(8);
        ihold_irun.set_irun(16);

        tmc2209::send_write_request(uart_address, gconf, uart).unwrap();
        tmc2209::send_write_request(uart_address, vactual, uart).unwrap();
        tmc2209::send_write_request(uart_address, ihold_irun, uart).unwrap();

        enable_pin.set_low();

        Self {
            uart,
            uart_address,
            step_pin,
            dir_pin,
            enable_pin,
        }
    }

    pub fn set_velocity(&mut self, velocity: i32) -> Result<(), Error> {
        let mut vactual = tmc2209::reg::VACTUAL::default();
        vactual.set(velocity);

        tmc2209::send_write_request(self.uart_address, vactual, &mut self.uart)
    }
}
