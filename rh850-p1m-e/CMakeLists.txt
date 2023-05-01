cmake_minimum_required(VERSION 3.13)

include(/usr/share/pico-sdk/pico_sdk_init.cmake)
project(glitcher)
pico_sdk_init()

# rest of your project
add_executable(glitcher
    main.c
)

target_link_libraries(glitcher pico_stdlib)
pico_add_extra_outputs(glitcher)
pico_enable_stdio_usb(glitcher 1)


