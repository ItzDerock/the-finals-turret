use core::num::ParseIntError;
use defmt::{Format, Formatter};

#[derive(Debug, Format)]
pub enum MotorAxis {
    Pan,
    Tilt,
}

#[derive(Debug, Format)]
pub struct MotorSpeed {
    pub axis: MotorAxis,
    pub velocity: i32,
}

pub enum Message {
    Speed(MotorSpeed),
    Stop(MotorAxis),
}

#[derive(Debug)]
pub enum DecodeError {
    InvalidCommand,
    InvalidAxis,
    InvalidInteger,
}

impl From<ParseIntError> for DecodeError {
    fn from(_value: ParseIntError) -> Self {
        DecodeError::InvalidInteger
    }
}

impl Format for DecodeError {
    fn format(&self, fmt: Formatter) {
        match self {
            DecodeError::InvalidCommand => defmt::write!(fmt, "Invalid command"),
            DecodeError::InvalidAxis => defmt::write!(fmt, "Invalid axis"),
            DecodeError::InvalidInteger => defmt::write!(fmt, "Invalid integer"),
        }
    }
}

/**
 * Decode a message from the USB controller.
 *
 * Commands:
 *   - v{axis_index}{velocity;f32} - Set the speed of a motor.
 *   - s{axis_index} - Stop a motor.
 */
pub fn decode(message: &str) -> Result<Message, DecodeError> {
    let mut chars = message.chars();
    let command = chars.next().ok_or(DecodeError::InvalidAxis)?;
    let axis_index = chars
        .next()
        .ok_or(DecodeError::InvalidAxis)?
        .to_digit(10)
        .ok_or(DecodeError::InvalidAxis)?;
    let axis = match axis_index {
        0 => MotorAxis::Pan,
        1 => MotorAxis::Tilt,
        _ => return Err(DecodeError::InvalidAxis),
    };

    match command {
        'v' => {
            let velocity = chars.as_str().parse::<i32>()?;
            let speed = MotorSpeed { axis, velocity };
            Ok(Message::Speed(speed))
        }
        's' => Ok(Message::Stop(axis)),
        _ => Err(DecodeError::InvalidCommand),
    }
}
