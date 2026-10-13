#include <assert.h>
#include <stdio.h>
#include "x622_xapp.h"

static unsigned draws, exits;
static int32_t levels, display_error;
static uint32_t exit_color;

int32_t x622_input_state(void) { return levels; }
int32_t x622_exit(void) { ++exits; return 0; }
int32_t x622_gfx_submit(const x622_gfx_command_t *commands, uint32_t bytes,
                      int32_t x, int32_t y, int32_t width, int32_t height) {
    (void)x; (void)y; (void)width; (void)height;
    assert(bytes == 3 * sizeof(*commands));
    exit_color = commands[2].color;
    ++draws;
    return display_error;
}

#include "../examples/hello/main.c"

int main(void) {
    unsigned i;
    levels = X622_HELD_CONFIRM;
    xapp_init();
    xapp_event(1, X622_INPUT_DOWN, 0, 0, 0);
    assert(draws == 1 && exits == 0);
    levels = 0;
    xapp_tick(100);
    for (i = 0; i < 30; ++i) xapp_tick(200 + i * 100);
    assert(draws == 1);
    xapp_event(1, X622_INPUT_DOWN, 0, 40, 0);
    assert(draws == 2 && exit_color == 0x7fff);
    xapp_event(1, X622_INPUT_DOWN, 0, 800, 0);
    assert(draws == 2);
    xapp_event(1, X622_INPUT_CONFIRM, 0, 40, 0);
    assert(exits == 1 && draws == 2);
    display_error = -4;
    xapp_init();
    xapp_tick(4000);
    xapp_event(1, X622_INPUT_CONFIRM, 0, 40, 0);
    assert(exits == 2);
    puts("PASS: release gate, idle redraw, selection, long release, explicit exit and display failure exit");
    return 0;
}
