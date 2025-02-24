use core::{
    borrow::BorrowMut,
    fmt::{Debug, Display},
    future::Future,
};

use embassy_stm32::{
    gpio::{AnyPin, Level, Output, Speed},
    mode::Async,
    usart::{Error, Uart},
};
use embassy_sync::{blocking_mutex::raw::CriticalSectionRawMutex, mutex};
use tmc2209::{reg::IFCNT, Reader};

pub type UartAsyncMutex = mutex::Mutex<CriticalSectionRawMutex, Uart<'static, Async>>;

pub struct Motor<'d> {
    uart: &'static UartAsyncMutex,
    uart_address: u8,
    step_pin: Output<'d>,
    dir_pin: Output<'d>,
    enable_pin: Output<'d>,
    regs: TmcRegisters,
    reader: Reader,
}

struct TmcRegisters {
    gconf: tmc2209::reg::GCONF,
    vactual: tmc2209::reg::VACTUAL,
}

impl<'d> Motor<'d> {
    pub async fn new(
        uart: &'static UartAsyncMutex,
        uart_address: u8,
        step_pin: AnyPin,
        dir_pin: AnyPin,
        enable_pin: AnyPin,
    ) -> Motor<'d> {
        let step_pin = Output::new(step_pin, Level::High, Speed::VeryHigh);
        let dir_pin = Output::new(dir_pin, Level::High, Speed::VeryHigh);
        let mut enable_pin = Output::new(enable_pin, Level::High, Speed::VeryHigh);

        // configure the registers
        // PDN_DISABLE: 1
        let mut gconf = tmc2209::reg::GCONF::default();
        gconf.set_pdn_disable(true);

        let vactual = tmc2209::reg::VACTUAL::ENABLED_STOPPED;

        let mut ihold_irun = tmc2209::reg::IHOLD_IRUN::default();
        ihold_irun.set_ihold(8);
        ihold_irun.set_irun(16);

        // stealthchop
        let mut chopconf = tmc2209::reg::CHOPCONF::default();
        // chopconf.set_t

        let mut guard = uart.lock().await;
        let mut uart_mut = guard.borrow_mut();
        {
            let uart_mut: &mut Uart<'static, embassy_stm32::mode::Async> = &mut *guard;
            tmc2209::send_write_request(uart_address, gconf, uart_mut).unwrap();
            tmc2209::send_write_request(uart_address, vactual, uart_mut).unwrap();
            tmc2209::send_write_request(uart_address, ihold_irun, uart_mut).unwrap();
            tmc2209::send_read_request::<tmc2209::reg::IFCNT, Uart<'static, Async>>(
                uart_address,
                uart_mut,
            )
            .unwrap();
            uart_mut.flush().await.unwrap();
        }

        let regs = TmcRegisters { gconf, vactual };
        let reader = tmc2209::Reader::default();

        // tmc2209::send_write_request(uart_address, gconf, &mut *uart_inst).unwrap();
        // tmc2209::send_write_request(uart_address, vactual, &mut *uart_inst).unwrap();
        // tmc2209::send_write_request(uart_address, ihold_irun, &mut *uart_inst).unwrap();
        // uart_inst.flush().await.unwrap();

        enable_pin.set_low();

        Self {
            uart,
            uart_address,
            step_pin,
            dir_pin,
            enable_pin,
            regs,
            reader,
        }
    }

    async fn write_register<T: tmc2209::WritableRegister>(
        &mut self,
        register: T,
    ) -> Result<(), Error> {
        let mut guard = self.uart.lock().await;
        let mut uart_mut = guard.borrow_mut();
        {
            let uart_mut: &mut Uart<'static, embassy_stm32::mode::Async> = &mut *guard;
            tmc2209::send_write_request(self.uart_address, register, uart_mut).unwrap();
            uart_mut.flush().await
        }
    }

    pub async fn set_velocity(&mut self, velocity: i32) {
        let mut vactual = tmc2209::reg::VACTUAL::default();
        vactual.set(velocity);

        self.write_register(vactual).await.unwrap();

        // read and print to debug
        let mut guard = self.uart.lock().await;
        let mut uart_mut = guard.borrow_mut();
        {
            let uart_mut: &mut Uart<'static, embassy_stm32::mode::Async> = &mut *guard;
            let drvstat = tmc2209::send_read_request::<
                tmc2209::reg::DRV_STATUS,
                Uart<'static, Async>,
            >(self.uart_address, uart_mut);

            defmt::info!("VACTUAL: {:?}", drvstat.unwrap());
        }
    }

    pub fn read_loop(&self) -> impl Future<Output = ()> {
        let uart = self.uart;

        async {
            // read forever
            let mut buffer = [0u8; 64];
            let mut reader = Reader::default();

            while let Ok(_b) = uart.lock().await.read(&mut buffer).await {
                if let (_, Some(response)) = reader.read_response(&buffer) {
                    match response.crc_is_valid() {
                        true => defmt::info!("Received valid response!"),
                        false => {
                            defmt::error!("Received invalid response!");
                            continue;
                        }
                    }

                    match response.reg_addr() {
                        Ok(tmc2209::reg::Address::IFCNT) => {
                            // let reg = response.register::<tmc2209::reg::IFCNT>().unwrap();
                            // Format not implemented for `tmc2209::reg::IFCNT`
                            // so need to print the value directly
                            let bytes = response.bytes();

                            defmt::info!("IFCNT: 0b{:08b}", bytes[0]);
                        }
                        Ok(addr) => {
                            defmt::info!("Addr: 0x{:X}", addr as u8);
                        }
                        Err(_err) => {
                            defmt::warn!("Error reading register address")
                        }
                    }
                }
            }
        }
    }

    // pub async fn move_steps(&mut self, steps: i32) {
    //     let mut step = tmc2209::reg::TSTEP::default();
    //     step.

    //     self.write_register(step).await.unwrap();
    // }
}
