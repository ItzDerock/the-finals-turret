use crate::{Irqs, Motor};
use defmt::{error, info};
use embassy_stm32::gpio::Pin;
use embassy_stm32::mode::Async;
use embassy_stm32::usart::BufferedUart;
use embassy_stm32::{peripherals, usart::Uart};

pub struct ControllerPeripherials {
    pub usart4: peripherals::USART4,
    pub uart_rx: peripherals::PC11,
    pub uart_tx: peripherals::PC10,
    pub uart_dma_rx: peripherals::DMA2_CH5,
    pub uart_dma_tx: peripherals::DMA2_CH3,

    pub motor_x_step: peripherals::PB13,
    pub motor_x_dir: peripherals::PB12,
    pub motor_x_en: peripherals::PB14,
}

pub struct Controller {
    uart: Uart<'static, embassy_stm32::mode::Async>,
    motor_x: Motor<'static>,
    // motor_y: Motor<'static>,
    // motor_z: Motor<'static>,
}

impl Controller {
    pub fn new(mut p: ControllerPeripherials) -> Self {
        // Initialize USART4
        // RX4: PC11
        // TX4: PC10
        let mut uart_config = embassy_stm32::usart::Config::default();
        uart_config.baudrate = 115200;
        let mut uart = Uart::new(
            p.usart4,
            p.uart_rx,
            p.uart_tx,
            Irqs,
            p.uart_dma_rx,
            p.uart_dma_tx,
            uart_config,
        )
        .unwrap();

        tmc2209::send_write_request(0, tmc2209::reg::GCONF::default(), &mut uart);

        // init tmc driver
        // let mut motor_x = Motor::new(
        //     &mut uart,
        //     2,
        //     p.motor_x_step.degrade(), // step
        //     p.motor_x_dir.degrade(),  // dir
        //     p.motor_x_en.degrade(),   // en
        // );

        if let Err(err) = motor_x.set_velocity(30) {
            error!("Error setting velocity: {:?}", err);
        }

        info!("Velocity set!");

        Self { uart, motor_x }
    }
}
