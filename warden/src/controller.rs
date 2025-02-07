use crate::{motor::UartAsyncMutex, Motor};
use defmt::{error, info};
use embassy_stm32::{gpio::Pin, mode::Async, peripherals, usart::Uart};

pub struct ControllerPeripherials {
    pub uart: &'static UartAsyncMutex,

    pub motor_x_address: u8,
    pub motor_x_step: peripherals::PB13,
    pub motor_x_dir: peripherals::PB12,
    pub motor_x_en: peripherals::PB14,

    pub motor_y_address: u8,
    pub motor_y_step: peripherals::PB11,
    pub motor_y_dir: peripherals::PB10,
    pub motor_y_en: peripherals::PB2,

    pub motor_z_address: u8,
    pub motor_z_step: peripherals::PB1,
    pub motor_z_dir: peripherals::PB0,
    pub motor_z_en: peripherals::PC5,
}

pub struct Controller<'d> {
    pub motor_x: Motor<'d>,
    pub motor_y: Motor<'d>,
    pub motor_z: Motor<'d>,
}

impl<'d> Controller<'d> {
    pub async fn new(p: ControllerPeripherials) -> Self {
        // init tmc driver
        let mut motor_x = Motor::new(
            p.uart,
            p.motor_x_address,
            p.motor_x_step.degrade(), // step
            p.motor_x_dir.degrade(),  // dir
            p.motor_x_en.degrade(),   // en
        )
        .await;

        let mut motor_y = Motor::new(
            p.uart,
            p.motor_y_address,
            p.motor_y_step.degrade(), // step
            p.motor_y_dir.degrade(),  // dir
            p.motor_y_en.degrade(),   // en
        )
        .await;

        let mut motor_z = Motor::new(
            p.uart,
            p.motor_z_address,
            p.motor_z_step.degrade(), // step
            p.motor_z_dir.degrade(),  // dir
            p.motor_z_en.degrade(),   // en
        )
        .await;

        Self {
            motor_x,
            motor_y,
            motor_z,
        }
    }
}
