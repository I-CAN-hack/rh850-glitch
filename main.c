#include <stdio.h>
#include "pico/stdlib.h"
#include "pico/bootrom.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"

// b'\x01\x00\x01\x00\xff\x03
const uint GLITCH_PIN = 2;

int main() {
    stdio_init_all();
    setup_default_uart();

    uart_init(uart0, 9600);
    gpio_set_function(0, GPIO_FUNC_UART);
    gpio_set_function(1, GPIO_FUNC_UART);

    gpio_init(GLITCH_PIN);
    gpio_set_dir(GLITCH_PIN, GPIO_OUT);
    gpio_set_slew_rate(GLITCH_PIN, GPIO_SLEW_RATE_FAST);
    gpio_set_drive_strength(GLITCH_PIN, GPIO_DRIVE_STRENGTH_12MA);
    gpio_put(GLITCH_PIN, 0);

    int delay = 0;
    int width = 10;

    char buf[128];
    int cnt = 0;

    int min_delay = clock_get_hz(clk_sys) / 1200;
    int real_delay = min_delay;

    while (true) {
      while (true) {
        int c = getchar_timeout_us(1);
        if (c == PICO_ERROR_TIMEOUT) break;

        if (c == '\x03') {
        } else if (c == 'r') {
          reset_usb_boot(0,0);
        } else if (c == '\n') {
          buf[cnt] = '\x00';
          sscanf(buf, "%d %d\n", &delay, &width);
          real_delay = min_delay + delay;
          cnt = 0;
        } else if (c == '$') {
          cnt = 0;
        } else {
          buf[cnt++] = (char)c;
          if (cnt >= sizeof(buf)) cnt = 0;
        }

      }

      if (uart_getc(uart0) != '\x01') continue;
      if (uart_getc(uart0) != '\x00') continue;
      if (uart_getc(uart0) != '\x01') continue;
      if (uart_getc(uart0) != '\x00') continue;
      if (uart_getc(uart0) != '\xff') continue;

      busy_wait_at_least_cycles(real_delay);
      gpio_put(GLITCH_PIN, 1);
      busy_wait_at_least_cycles(width);
      gpio_put(GLITCH_PIN, 0);

      printf("glitch %d %d\n", delay, width);

    }
    return 0;
}
