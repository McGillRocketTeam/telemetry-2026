#include <cstdint>


typedef struct __attribute__((__packed__)) command_packet_data {
    uint8_t command_id;
    char command_string[2];
} command_packet_data;

typedef union command_packet {
    command_packet_data data;
    uint8_t bytes[sizeof(command_packet_data)];
} command_packet;