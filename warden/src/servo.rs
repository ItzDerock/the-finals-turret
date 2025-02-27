use embassy_stm32::timer::{
    simple_pwm::{SimplePwm, SimplePwmChannel},
    GeneralInstance4Channel,
};
use embedded_hal::pwm;

pub struct Servo<'a, T: GeneralInstance4Channel> {
    pwm: &'a mut SimplePwmChannel<'a, T>,
    max_duty: u16,
}

impl<'a, T: GeneralInstance4Channel> Servo<'a, T> {
    pub fn new(pwm: &'a mut SimplePwmChannel<'a, T>) -> Self {
        let max_duty = pwm.max_duty_cycle();
        pwm.enable();

        Self { pwm, max_duty }
    }

    /**
     * Angle between 0 and 180.
     */
    pub fn set_position(&mut self, angle: u8) {
        let duty = (angle as f32 / 180.0) * self.max_duty as f32;
        self.pwm.set_duty_cycle(duty as u16);
    }
}
