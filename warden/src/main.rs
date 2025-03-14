#![no_std]
#![no_main]

use controller::{Controller, ControllerPeripherials};
use defmt::*;
use embassy_executor::Spawner;
use embassy_futures::join::join;
use embassy_stm32::gpio::{AnyPin, Level, Output, OutputType, Pin, Speed};
use embassy_stm32::peripherals::TIM16;
use embassy_stm32::time::Hertz;
use embassy_stm32::timer::low_level::CountingMode;
use embassy_stm32::timer::simple_pwm::{PwmPin, SimplePwm, SimplePwmChannel};
use embassy_stm32::wdg::IndependentWatchdog;
use embassy_stm32::{
    bind_interrupts, peripherals, usart, usart::Uart, usb as usb_interrupt, Config,
};
use embassy_time::Timer;
use motor::{Motor, UartAsyncMutex};
use servo::Servo;
use static_cell::StaticCell;
use usb::{USBController, USBPeripherals};
use {defmt_rtt as _, panic_probe as _};

use embassy_sync::{blocking_mutex::raw::CriticalSectionRawMutex, mutex};
pub type ControllerMutex = mutex::Mutex<CriticalSectionRawMutex, Controller<'static, TIM16>>;

mod controller;
mod decoder;
mod motor;
mod servo;
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
    let uart = Uart::new(
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

    // First define the static for the PWM peripheral
    static PWM: StaticCell<SimplePwm<TIM16>> = StaticCell::new();

    // Create and initialize the PWM peripheral inside the static
    let servo_pin = PwmPin::new_ch1(p.PD0, OutputType::PushPull);
    let pwm = PWM.init(SimplePwm::new(
        p.TIM16,
        Some(servo_pin),
        None,
        None,
        None,
        Hertz(50_000),
        CountingMode::EdgeAlignedUp,
    ));

    // Now we can get the channel from the static PWM
    static SERVO_PWM: StaticCell<SimplePwmChannel<'static, TIM16>> = StaticCell::new();
    let servo_pwm = SERVO_PWM.init(pwm.ch4());

    // Initialize the servo with the static PWM channel
    static SERVO: StaticCell<Servo<'static, TIM16>> = StaticCell::new();
    let servo = SERVO.init(Servo::new(servo_pwm)); // init pwm for servo control

    // let servo_pin = PwmPin::new_ch1(p.PD0, OutputType::PushPull);
    // let mut servo_pwm = SimplePwm::new(
    //     p.TIM16,
    //     Some(servo_pin),
    //     None,
    //     None,
    //     None,
    //     Hertz(50_000),
    //     CountingMode::EdgeAlignedUp,
    // );

    // static SERVO: StaticCell<Servo<'static, TIM16>> = StaticCell::new();

    // // Extract the channel before the original pwm is dropped
    // let ch4 = temp_pwm.ch4();
    // static SERVO_PWM: StaticCell<SimplePwmChannel<'static, TIM16>> = StaticCell::new();
    // let mut servo_pwm = SERVO_PWM.init(ch4);

    // let servo = SERVO.init(Servo::new(servo_pwm));

    let controller = Controller::new(
        ControllerPeripherials {
            uart,

            // MS0: GND, MS1: GND
            motor_x_address: 0b00,
            motor_x_step: p.PB13.degrade(),
            motor_x_dir: p.PB12.degrade(),
            motor_x_en: p.PB14.degrade(),

            // MS0: GND, MS1: 3.3V
            motor_y_address: 0b01,
            motor_y_step: p.PB10.degrade(),
            motor_y_dir: p.PB2.degrade(),
            motor_y_en: p.PB11.degrade(),

            // MS0: 3.3V, MS1: GND
            motor_z_address: 0b10,
            motor_z_step: p.PB0.degrade(),
            motor_z_dir: p.PC5.degrade(),
            motor_z_en: p.PB1.degrade(),

            trigger_servo: servo,
        },
        spawner.make_send(),
    )
    .await;

    static CONTROLLER: StaticCell<ControllerMutex> = StaticCell::new();
    let controller = CONTROLLER.init(mutex::Mutex::new(controller));

    let mut usb = USBController::new(USBPeripherals {
        controller,
        usb: p.USB,
        usb_dp: p.PA12,
        usb_dm: p.PA11,
    });

    let usb_fut = usb.listen();

    // Run everything concurrently.
    // If we had made everything `'static` above instead, we could do this using separate tasks instead.
    join(usb_fut, wdg_fut).await;
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
