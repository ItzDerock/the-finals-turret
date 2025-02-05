#![no_std]
#![no_main]

use controller::{Controller, ControllerPeripherials};
use defmt::{panic, *};
use embassy_executor::Spawner;
use embassy_futures::join::join;
use embassy_stm32::gpio::{AnyPin, Level, Output, Pin, Speed};
use embassy_stm32::wdg::IndependentWatchdog;
use embassy_stm32::{bind_interrupts, peripherals, usart, usb as usb_interrupt, Config};
use embassy_time::Timer;
use embassy_usb::driver::EndpointError;
use motor::Motor;
use usb::{USBController, USBPeripherals};
use {defmt_rtt as _, panic_probe as _};

mod controller;
mod motor;
mod usb;

bind_interrupts!(struct Irqs {
    USB_UCPD1_2 => usb_interrupt::InterruptHandler<peripherals::USB>;
    USART3_4_5_6_LPUART1 => usart::InterruptHandler<peripherals::USART4>;
});

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let mut config = Config::default();
    {
        use embassy_stm32::rcc::*;
        config.rcc.hsi48 = Some(Hsi48Config {
            sync_from_usb: true,
        });
        config.rcc.mux.usbsel = mux::Usbsel::HSI48;
    }
    let mut p = embassy_stm32::init(config);

    // Enable the watchdog
    let mut wdg = IndependentWatchdog::new(p.IWDG, 2_000_000);

    info!("Hello World!");

    // Flash the builtin LED on PD8
    match spawner.spawn(flash_led(p.PD8.degrade())) {
        Ok(_) => info!("Flash LED task spawned!"),
        Err(_) => error!("Failed to spawn flash LED task!"),
    }

    let wdg_fut = async {
        loop {
            wdg.pet();
            Timer::after_millis(1_000).await;
        }
    };

    Controller::new(ControllerPeripherials {
        usart4: p.USART4,
        uart_rx: p.PC11,
        uart_tx: p.PC10,
        uart_dma_rx: p.DMA2_CH5,
        uart_dma_tx: p.DMA2_CH3,
        motor_x_step: p.PB13,
        motor_x_dir: p.PB12,
        motor_x_en: p.PB14,
    });

    let mut usb = USBController::new(USBPeripherals {
        usb: p.USB,
        usb_dp: p.PA12,
        usb_dm: p.PA11,
    });

    let usb_fut = usb.listen();

    // YEN PB11
    // YSTP PB10
    // YDIR PB2
    // let mut motor_y = Motor::new(
    //     &mut p.USART4,
    //     3,
    //     p.PC11, // rx
    //     p.PC10, // tx
    //     p.DMA2_CH5,
    //     p.DMA2_CH3,
    //     Irqs,
    //     p.PB11.degrade(), // step
    //     p.PB10.degrade(), // dir
    //     p.PB2.degrade(),  // en
    // );

    // // ZEN PB1
    // // ZSTP PB0
    // // ZDIR PC5
    // let mut motor_z = Motor::new(
    //     &mut p.USART4,
    //     4,
    //     p.PC11, // rx
    //     p.PC10, // tx
    //     p.DMA2_CH5,
    //     p.DMA2_CH3,
    //     Irqs,
    //     p.PB1.degrade(), // step
    //     p.PB0.degrade(), // dir
    //     p.PC5.degrade(), // en
    // );

    // Run everything concurrently.
    // If we had made everything `'static` above instead, we could do this using separate tasks instead.
    join(usb_fut, wdg_fut).await;
}

struct Disconnected {}

impl From<EndpointError> for Disconnected {
    fn from(val: EndpointError) -> Self {
        match val {
            EndpointError::BufferOverflow => panic!("Buffer overflow"),
            EndpointError::Disabled => Disconnected {},
        }
    }
}

// task to flash an LED
#[embassy_executor::task(pool_size = 1)]
async fn flash_led(p: AnyPin) {
    let mut output = Output::new(p, Level::Low, Speed::Low);

    loop {
        output.set_low();
        Timer::after_millis(1000).await;
        output.set_high();
        Timer::after_millis(1000).await;
    }
}
