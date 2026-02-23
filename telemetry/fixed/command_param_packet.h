#include <cstdint>

// Command string supports up to 4 characters
// It must be null terminated

// this packet supports up to 3 parameters 
// checking the size vs the normal cmd pkt to know which to choose
typedef struct __attribute__((__packed__)) command_param_packet_data {
    uint8_t command_id;
    char command_string[5];
    float arg1;
    float arg2;
    float arg3;
} command_param_packet_data;

typedef union command_param_packet {
    command_param_packet_data data;
    uint8_t bytes[sizeof(command_param_packet_data)];
} command_param_packet;