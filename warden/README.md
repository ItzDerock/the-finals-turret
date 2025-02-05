# Microcontroller Code

Embassy project, targets STM32G0 microcontroller.

## Requirements
- cargo-binutils
- rust with llvm-tools component
- target `thumbv7em-none-eabihf`

## Build
Run the following command to create a binary firmware file:
```sh
cargo objcopy --release -- -O binary firmware.bin
```

and flash that firmware.bin to the microcontroller.
On the SKR Mini E3 v3.0 board, you just move the firmware.bin to an SD card (MUST be <8GB, single FAT32 partition) and insert it to the board.
You will know the flashing is successful when the status LED stops blinking and the firmware file is renamed to FIRMWARE.CUR.

Cannot just use `cargo build --release` as that generates an ELF file, which contains metadata that the bootloader does not understand.

## Debug

It is recommended that you have some sort of SWD debugger to debug the firmware.
