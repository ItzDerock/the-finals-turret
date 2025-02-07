#![no_std]
#![no_main]

use controller::{Controller, ControllerPeripherials};
use defmt::*;
use embassy_executor::Spawner;
use embassy_futures::join::join;
use embassy_stm32::gpio::{AnyPin, Level, Output, Pin, Speed};
use embassy_stm32::wdg::IndependentWatchdog;
use embassy_stm32::{
    bind_interrupts, peripherals, usart, usart::Uart, usb as usb_interrupt, Config,
};
use embassy_sync::mutex;
use embassy_time::Timer;
use motor::{Motor, UartAsyncMutex};
use static_cell::StaticCell;
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
    let p = embassy_stm32::init(config);

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

    // Initialize USART4
    // RX4: PC11
    // TX4: PC10
    let mut uart_config = embassy_stm32::usart::Config::default();
    uart_config.baudrate = 115200;
    let mut uart = Uart::new(
        p.USART4,
        p.PC11,
        p.PC10,
        Irqs,
        p.DMA2_CH5,
        p.DMA2_CH3,
        uart_config,
    )
    .unwrap();

    static UART: StaticCell<UartAsyncMutex> = StaticCell::new();
    let uart = UART.init(mutex::Mutex::new(uart));

    let mut controller = Controller::new(ControllerPeripherials {
        uart,

        // MS0: GND, MS1: GND
        motor_x_address: 0b00,
        motor_x_step: p.PB13,
        motor_x_dir: p.PB12,
        motor_x_en: p.PB14,

        // MS0: GND, MS1: 3.3V
        motor_y_address: 0b01,
        motor_y_step: p.PB11,
        motor_y_dir: p.PB10,
        motor_y_en: p.PB2,

        // MS0: 3.3V, MS1: GND
        motor_z_address: 0b10,
        motor_z_step: p.PB1,
        motor_z_dir: p.PB0,
        motor_z_en: p.PC5,
    })
    .await;

    let mut usb = USBController::new(USBPeripherals {
        usb: p.USB,
        usb_dp: p.PA12,
        usb_dm: p.PA11,
    });

    let usb_fut = usb.listen();
    let read_loop_fut = controller.motor_x.read_loop();

    controller.motor_x.set_velocity(5000).await;
    info!("Velocity set!");

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
    join(usb_fut, join(wdg_fut, read_loop_fut)).await;
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
