import utime
import _thread #for using both cores on the pico
from machine import Pin, SPI
from nrf24l01 import NRF24L01
from servo import Servo

RX_ADDR = b"\xd2\xf0\xf0\xf0\xf0"   #this devices RX address
TX_ADDR = b"\xe1\xf0\xf0\xf0\xf0"
CMD_RELEASE = 0x01

spi = SPI(0, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
csn = Pin(17, mode=Pin.OUT)
ce  = Pin(20, mode=Pin.OUT)

nrf = NRF24L01(spi, csn, ce, channel=76, payload_size=32)
nrf.open_rx_pipe(1, RX_ADDR)
nrf.open_tx_pipe(TX_ADDR)
nrf.start_listening()

led = Pin("LED", Pin.OUT)
led.value(0)

#circular array for bomb dropping
bomb1 = Servo(10)
bomb2 = Servo(11)
bomb3 = Servo(12)
bombs = [bomb1, bomb2, bomb3]

for b in bombs:
    b.write(0)

#shared data between cores
switch_state = "OFF"
switch_lock = _thread.allocate_lock()


def read_pwm_thread():
    global switch_state
    masterSignalPin = Pin(13, Pin.IN)
    prev = masterSignalPin.value()
    rise_time = 0
    threshold = 1500  #microseconds

    while True:
        curr = masterSignalPin.value()

        if prev == 0 and curr == 1:  #rising edge
            rise_time = utime.ticks_us()

        elif prev == 1 and curr == 0:  #falling edge
            pulse = utime.ticks_diff(utime.ticks_us(), rise_time)
            if 900 <= pulse <= 2100:  #valid range
                with switch_lock:
                    if pulse > threshold:
                        switch_state = "ON"
                    else:
                        switch_state = "OFF"
        prev = curr
        utime.sleep_us(50)

#start pwm signal reading on core 1
_thread.start_new_thread(read_pwm_thread, ())

print("Receiver ready... listening for CMD_RELEASE")

count = 0

#reset servo after delay
def reset_servo_after_delay(bomb_idx, delay_ms=2000):
    utime.sleep_ms(delay_ms)
    bombs[bomb_idx].write(0)
    print(f"Bomb {bomb_idx + 1} reset to 0°")

#main loop on primary core
while True:
    if nrf.any():
        packet = nrf.recv()
        cmd = packet[0]

        with switch_lock:
            current_state = switch_state

        if cmd == CMD_RELEASE and current_state == "ON":
            led.toggle()
            count = (count % 3)  #0, 1, 2
            print(f"Releasing bomb {count + 1} (switch={current_state})")

            #move servo to release position
            bombs[count].write(180)

            #start a new temporary thread to reset it after 2 seconds
            _thread.start_new_thread(reset_servo_after_delay, (count,))

            #move to next bomb for next release
            count = (count + 1) % 3

        else:
            print(f"Ignored CMD (switch={current_state})")

    utime.sleep_ms(10)


