use crate::{decoder, ControllerMutex, Irqs};
use defmt::{info, panic, Format};
use embassy_futures::join::join;
use embassy_stm32::peripherals::{PA11, PA12, USB};
use embassy_stm32::usb::Driver;
use embassy_usb::class::cdc_acm::{CdcAcmClass, State};
use embassy_usb::driver::EndpointError;
use embassy_usb::{Builder, UsbDevice};
use static_cell::StaticCell;

pub struct USBPeripherals {
    pub controller: &'static ControllerMutex,
    pub usb: USB,
    pub usb_dp: PA12,
    pub usb_dm: PA11,
}

pub struct USBController {
    class: CdcAcmClass<'static, Driver<'static, USB>>,
    usb: UsbDevice<'static, Driver<'static, USB>>,
    controller: &'static ControllerMutex,
}

static STATE: StaticCell<State> = StaticCell::new();
static CONFIG_DESCRIPTOR: StaticCell<[u8; 256]> = StaticCell::new();
static BOS_DESCRIPTOR: StaticCell<[u8; 256]> = StaticCell::new();
static CONTROL_BUF: StaticCell<[u8; 64]> = StaticCell::new();
static MSOS_DESCRIPTOR: StaticCell<[u8; 64]> = StaticCell::new();

impl USBController {
    pub fn new(p: USBPeripherals) -> Self {
        // Create the driver from the HAL.
        let driver = Driver::new(p.usb, Irqs, p.usb_dp, p.usb_dm);

        // Create embassy-usb Config.
        let mut config = embassy_usb::Config::new(0xc0de, 0xcafe);
        config.manufacturer = Some("DerocksCoolProducts");
        config.product = Some("Warden");
        config.serial_number = Some("");
        config.device_class = 0xEF;
        config.device_sub_class = 0x02;
        config.device_protocol = 0x01;
        config.composite_with_iads = true;

        // Leak buffers to give them a 'static lifetime.
        let config_descriptor = CONFIG_DESCRIPTOR.init([0; 256]);
        let bos_descriptor = BOS_DESCRIPTOR.init([0; 256]);
        let control_buf = CONTROL_BUF.init([0; 64]);
        let msos_descriptor = MSOS_DESCRIPTOR.init([0; 64]);
        let state = STATE.init(State::new());

        // Create the Builder.
        let mut builder = Builder::new(
            driver,
            config,
            // Pass mutable references to our owned buffers.
            config_descriptor,
            bos_descriptor,
            msos_descriptor,
            control_buf,
        );

        // Create the class using the builder and the state.
        // The builder will store references into our buffers and state,
        // so these must live as long as the USBController.
        let class = CdcAcmClass::new(&mut builder, state, 64);

        // Build the USB device.
        let usb = builder.build();

        Self {
            class,
            usb,
            controller: p.controller,
        }
    }

    pub async fn listen(&mut self) {
        let usb = &mut self.usb;
        let class = &mut self.class;
        let controller = self.controller;

        let usb_fut = usb.run();
        let listen_fut = async {
            loop {
                class.wait_connection().await;
                info!("Connected");
                if let Err(e) = USBController::receive(controller, class).await {
                    defmt::warn!("Receive error: {:?}", e);
                }
                info!("Disconnected");
            }
        };

        join(usb_fut, listen_fut).await;
    }

    async fn receive(
        controller: &ControllerMutex,
        class: &mut CdcAcmClass<'static, Driver<'static, USB>>,
    ) -> Result<(), Disconnected> {
        let mut buf = [0u8; 64];
        let mut utf8_buf = [0u8; 128]; // Buffer for partial UTF-8 sequences
        let mut buf_len = 0;

        loop {
            let n = class.read_packet(&mut buf).await?;
            let data = &buf[..n];

            // Check if we have enough space in the UTF-8 buffer.
            if buf_len + data.len() > utf8_buf.len() {
                buf_len = 0; // Reset buffer on overflow (a simple strategy)
            }

            // Add the new data to the buffer.
            utf8_buf[buf_len..buf_len + data.len()].copy_from_slice(data);
            buf_len += data.len();

            // Attempt to decode as much as possible.
            let (_valid, remaining) = match core::str::from_utf8(&utf8_buf[..buf_len]) {
                Ok(s) => {
                    info!("Received: {}", s);
                    USBController::execute_command(s, controller).await;
                    (s.len(), 0)
                }
                Err(e) => {
                    let valid_len = e.valid_up_to();
                    if valid_len > 0 {
                        if let Ok(s) = core::str::from_utf8(&utf8_buf[..valid_len]) {
                            info!("Received: {}", s);
                            USBController::execute_command(s, controller).await;
                        }
                    }
                    // Calculate the number of bytes remaining that could be part of a valid sequence.
                    let error_len = e.error_len().unwrap_or(0);
                    (valid_len, buf_len - valid_len - error_len)
                }
            };

            // Keep any remaining bytes for the next iteration.
            if remaining > 0 {
                utf8_buf.copy_within(buf_len - remaining..buf_len, 0);
            }
            buf_len = remaining;
        }
    }

    pub async fn execute_command(message: &str, controller: &ControllerMutex) {
        let message = message.trim();

        // ignore empty lines or lines that only contain \n
        if message.is_empty() {
            return;
        }

        let ok = async || -> Result<(), embassy_stm32::usart::Error> {
            match decoder::decode(message) {
                Ok(decoder::Message::Speed(speed)) => match speed.axis {
                    decoder::MotorAxis::Pan => {
                        controller
                            .lock()
                            .await
                            .motor_x
                            .set_velocity(speed.velocity)
                            .await?;
                    }
                    decoder::MotorAxis::Tilt => {
                        let mut controller = controller.lock().await;
                        controller.motor_y.set_velocity(speed.velocity).await?;
                        controller.motor_z.set_velocity(-1 * speed.velocity).await?;
                    }
                },
                Ok(decoder::Message::Stop(axis)) => {
                    info!("Stop: {:?}", axis);
                }
                Ok(decoder::Message::Trigger(status)) => {
                    info!("Trigger: {:?}", status);
                    controller
                        .lock()
                        .await
                        .trigger_servo
                        .set_position(if status { 180 } else { 0 });
                }
                Err(e) => {
                    defmt::warn!("Error decoding message: {:?}", e);
                }
            };

            Ok(())
        };

        if let Err(e) = ok().await {
            defmt::warn!("Error executing command: {:?}", e);
        }
    }
}

impl Format for Disconnected {
    fn format(&self, fmt: defmt::Formatter) {
        defmt::write!(fmt, "Disconnected");
    }
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
