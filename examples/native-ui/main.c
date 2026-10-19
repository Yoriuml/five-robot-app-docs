#include "x622_xapp.h"

static uint32_t armed, selected, failed;
static x622_ui_node_t nodes[3] = {
    { .id=1, .kind=X622_UI_RECT, .x=24, .y=56, .w=192, .h=128,
      .clip_w=240, .clip_h=240, .color=0x18e3, .radius=24, .opacity=255 },
    { .id=2, .kind=X622_UI_RECT, .x=40, .y=104, .w=48, .h=32,
      .clip_w=240, .clip_h=240, .color=0xff00, .radius=16, .opacity=255 },
    { .id=3, .kind=X622_UI_RECT, .x=112, .y=202, .w=16, .h=4,
      .clip_w=240, .clip_h=240, .color=0xffff, .radius=2, .opacity=255 }
};

void xapp_init(void) {
    const x622_ui_config_t config = {sizeof(config), 1, 0x0841, 20, 4096, 8, 0};
    armed=selected=failed=0;
    nodes[1].x=40;
    if (x622_ui_config(&config, sizeof(config)) < 0) { failed=1; return; }
    if (x622_ui_scene(nodes, sizeof(nodes), 0) < 0) failed=1;
}

void xapp_tick(uint64_t now_ms) {
    (void)now_ms;
    if (!armed && x622_input_state() == 0) armed=1;
}

void xapp_event(uint32_t type, uint32_t action, uint32_t phase, uint32_t held, uint32_t mask) {
    (void)phase; (void)mask;
    if (!armed || type != 1) return;
    if (action == X622_INPUT_CONFIRM && (held >= 2000 || failed)) {
        (void)x622_exit(); return;
    }
    if (held >= 600 || action == X622_INPUT_AUX) return;
    if (action == X622_INPUT_UP) selected=1;
    else if (action == X622_INPUT_DOWN) selected=0;
    else if (action == X622_INPUT_CONFIRM) selected=!selected;
    else return;
    if (failed) return;
    nodes[1].x = selected ? 152 : 40;
    nodes[1].color = selected ? 0x07ff : 0xff00;
    if (x622_ui_scene(nodes, sizeof(nodes), 280) < 0) failed=1;
}

void xapp_shutdown(void) { (void)x622_ui_config(0, 0); }
