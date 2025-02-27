use crate::{motor::UartAsyncMutex, servo::Servo, Motor};
use defmt::{error, info};
use embassy_executor::SendSpawner;
use embassy_stm32::timer::GeneralInstance4Channel;
use embassy_stm32::{
    gpio::{AnyPin, Pin},
    mode::Async,
    peripherals,
    usart::Uart,
};

pub struct ControllerPeripherials<'d, T: GeneralInstance4Channel> {
    pub uart: &'static UartAsyncMutex,

    pub motor_x_address: u8,
    pub motor_x_step: AnyPin,
    pub motor_x_dir: AnyPin,
    pub motor_x_en: AnyPin,

    pub motor_y_address: u8,
    pub motor_y_step: AnyPin,
    pub motor_y_dir: AnyPin,
    pub motor_y_en: AnyPin,

    pub motor_z_address: u8,
    pub motor_z_step: AnyPin,
    pub motor_z_dir: AnyPin,
    pub motor_z_en: AnyPin,

    pub trigger_servo: &'d mut Servo<'d, T>,
}

pub struct Controller<'d, T: GeneralInstance4Channel> {
    pub motor_x: Motor<'d>,
    pub motor_y: Motor<'d>,
    pub motor_z: Motor<'d>,
    pub trigger_servo: &'d mut Servo<'d, T>,
}

impl<'d, T: GeneralInstance4Channel> Controller<'d, T> {
    pub async fn new(p: ControllerPeripherials<'d, T>, spawner: SendSpawner) -> Self {
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

        // match (spawner.spawn(crate::motor::read_loop(p.uart))) {
        //     Ok(_) => info!("Spawned read loop"),
        //     Err(_) => error!("Failed to spawn read loop"),
        // }

        Self {
            motor_x,
            motor_y,
            motor_z,
            trigger_servo: p.trigger_servo,
        }
    }
}
