use crate::{Disconnected, Irqs};
use defmt::info;
use embassy_futures::join::join;
use embassy_stm32::peripherals::{PA11, PA12, USB};
use embassy_stm32::usb::Driver;
use embassy_usb::class::cdc_acm::{CdcAcmClass, State};
use embassy_usb::{Builder, UsbDevice};

pub struct USBPeripherals {
    pub usb: USB,
    pub usb_dp: PA12,
    pub usb_dm: PA11,
}

pub struct USBController<'a> {
    class: CdcAcmClass<'a, Driver<'a, USB>>,
    usb: UsbDevice<'a, Driver<'a, USB>>,
}

impl USBController<'_> {
    pub fn new(mut p: USBPeripherals) -> Self {
        // Create the driver, from the HAL.
        let driver = Driver::new(p.usb, Irqs, p.usb_dp, p.usb_dm);

        // Create embassy-usb Config
        let mut config = embassy_usb::Config::new(0xc0de, 0xcafe);
        config.manufacturer = Some("DerocksCoolProducts");
        config.product = Some("Warden");
        config.serial_number = Some("");
        config.device_class = 0xEF;
        config.device_sub_class = 0x02;
        config.device_protocol = 0x01;
        config.composite_with_iads = true;

        // Create embassy-usb DeviceBuilder using the driver and config.
        // It needs some buffers for building the descriptors.
        let mut config_descriptor = [0; 256];
        let mut bos_descriptor = [0; 256];
        let mut control_buf = [0; 64];
        let mut msos_descriptor = [0; 64];

        let mut state = State::new();
        let mut builder = Builder::new(
            driver,
            config,
            &mut config_descriptor,
            &mut bos_descriptor,
            &mut msos_descriptor,
            &mut control_buf,
        );

        // Create classes on the builder.
        let mut class = CdcAcmClass::new(&mut builder, &mut state, 64);

        // Build the builder.
        let mut usb = builder.build();
        Self { class, usb }
    }

    pub async fn listen(&mut self) -> dyn core::future::Future<Output = ()> {
        let usb_fut = self.usb.run();
        let listen_fut = async {
            loop {
                self.class.wait_connection().await;
                info!("Connected");
                self.recieve().await;
                info!("Disconnected");
            }
        };

        join(usb_fut, listen_fut)
    }

    async fn recieve(&mut self) -> Result<(), Disconnected> {
        let mut buf = [0; 64];
        let mut utf8_buf = [0u8; 128]; // Buffer for partial UTF-8 sequences
        let mut buf_len = 0;

        loop {
            let n = self.class.read_packet(&mut buf).await?;
            let data = &buf[..n];

            // Check if we have space
            if buf_len + data.len() > utf8_buf.len() {
                buf_len = 0; // Reset buffer if overflow (simple strategy)
            }

            // Add new data to buffer
            utf8_buf[buf_len..buf_len + data.len()].copy_from_slice(data);
            buf_len += data.len();

            // Try to decode as much as possible
            let (valid, remaining) = match core::str::from_utf8(&utf8_buf[..buf_len]) {
                Ok(s) => {
                    info!("Received: {}", s);
                    (s.len(), 0)
                }
                Err(e) => {
                    let valid_len = e.valid_up_to();
                    if valid_len > 0 {
                        if let Ok(s) = core::str::from_utf8(&utf8_buf[..valid_len]) {
                            info!("Received: {}", s);
                        }
                    }
                    (valid_len, buf_len - e.error_len().unwrap_or(buf_len))
                }
            };

            // Keep invalid bytes for next iteration
            if remaining > 0 {
                utf8_buf.copy_within(buf_len - remaining..buf_len, 0);
            }
            buf_len = remaining;
        }
    }
}
