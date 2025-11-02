from machine import Pin, SPI
from utime import sleep, sleep_ms
from nrf24l01 import NRF24L01

sleep(0.1)

RX_ADDR = b"\xe1\xf0\xf0\xf0\xf0"
TX_ADDR = b"\xd2\xf0\xf0\xf0\xf0"
CMD_RELEASE = 0x01

#nrf24 setup
spi = SPI(0, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
csn = Pin(17, mode=Pin.OUT)
ce  = Pin(20, mode=Pin.OUT)

nrf = NRF24L01(spi, csn, ce, channel=76, payload_size=32)

nrf.open_tx_pipe(RX_ADDR)
nrf.open_rx_pipe(1, TX_ADDR)
nrf.start_listening()

#button setup
buttonOld = 1
button = Pin(15, Pin.IN, Pin.PULL_UP)

print("Transmitter ready...")

while True:
    buttonNew = button.value()
    if buttonOld == 0 and buttonNew == 1:   #rising edge (button released)
        print("Button pressed → sending CMD_RELEASE")

        nrf.stop_listening()
        try:
            nrf.send(bytes([CMD_RELEASE]) + b"\x00" * 31)
            print("Sent CMD_RELEASE")
        except OSError:
            print("Send failed or timed out")
        nrf.start_listening()

        sleep_ms(100)

    buttonOld = buttonNew
    sleep_ms(50)
