#include "x622_xapp.h"

static uint32_t selected;
static uint32_t armed;
static uint32_t failed;
static uint32_t greeting;
static x622_gfx_command_t scene[3] = {
    { .opcode = X622_GFX_FILL_RECT, .w = 240, .h = 240, .color = 0x0861 },
    { .opcode = X622_GFX_TEXT, .flags = X622_GFX_TEXT_CENTER,
      .x = 120, .y = 82, .color = 0xffff, .arg0 = 2, .text = "Hello Five" },
    { .opcode = X622_GFX_TEXT, .flags = X622_GFX_TEXT_CENTER,
      .x = 120, .y = 142, .color = 0x632c, .arg0 = 2, .text = "Exit APP" }
};

static void draw(void) {
    scene[1].color = selected == 0 ? (greeting ? 0x7fff : 0xffff) : 0x632c;
    scene[2].color = selected == 1 ? 0x7fff : 0x632c;
    failed = x622_gfx_submit(scene, sizeof(scene), 0, 0, 240, 240) < 0;
}

void xapp_init(void) {
    selected = 0;
    armed = 0;
    failed = 0;
    greeting = 0;
    draw();
}

void xapp_tick(uint64_t now_ms) {
    (void)now_ms;
    if (!armed && x622_input_state() == 0) armed = 1;
}

void xapp_event(uint32_t type, uint32_t action, uint32_t phase,
                uint32_t held_ms, uint32_t pressed_mask) {
    uint32_t previous;
    (void)phase;
    (void)pressed_mask;
    if (!armed || type != 1 || held_ms >= 600) return;
    if (action == X622_INPUT_CONFIRM && (selected == 1 || failed)) {
        (void)x622_exit();
        return;
    }
    previous = selected;
    if (action == X622_INPUT_UP) selected = 0;
    if (action == X622_INPUT_DOWN) selected = 1;
    if (selected != previous) draw();
    else if (action == X622_INPUT_CONFIRM && selected == 0) {
        greeting = !greeting;
        draw();
    }
}
