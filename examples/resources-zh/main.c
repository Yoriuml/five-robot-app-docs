#include "x622_xapp.h"

/* The package owns the 240x240 background; the APP owns only three commands. */
static uint32_t armed, selected, failed;
static x622_gfx_command_t nodes[3] = {
    { .opcode=X622_GFX_STROKE_RECT, .x=20, .y=20, .w=200, .h=200,
      .color=0x07ff, .arg0=2 },
    { .opcode=X622_GFX_TEXT, .flags=X622_GFX_TEXT_CENTER, .x=120, .y=174,
      .color=0xffff, .arg0=2, .text="Exit APP" },
    { .opcode=X622_GFX_FILL_RECT, .x=104, .y=206, .w=32, .h=3, .color=0x07ff }
};
static void draw(void) {
    nodes[1].color = selected ? 0x07ff : 0x6b4d;
    if (x622_gfx_resource("hello.rgb565", 12, nodes, sizeof(nodes), 0, 0, 240, 240) < 0) failed=1;
}
void xapp_init(void) { armed=selected=failed=0; draw(); }
void xapp_tick(uint64_t now) { (void)now; if (!armed && x622_input_state()==0) armed=1; }
void xapp_event(uint32_t type,uint32_t action,uint32_t phase,uint32_t held,uint32_t mask) {
    (void)phase; (void)mask;
    if (!armed || type!=1 || held>=600) return;
    if (action==X622_INPUT_CONFIRM && (selected || failed)) { (void)x622_exit(); return; }
    if (action==X622_INPUT_DOWN && !selected) { selected=1; draw(); }
    else if (action==X622_INPUT_UP && selected) { selected=0; draw(); }
}
