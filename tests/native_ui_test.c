#include <assert.h>
#include "x622_xapp.h"
static int32_t levels, error;
static unsigned calls, exits, releases;
int32_t x622_input_state(void) { return levels; }
int32_t x622_exit(void) { ++exits; return 0; }
int32_t x622_ui_config(const x622_ui_config_t* c,uint32_t bytes) {
    if (!bytes) { ++releases; return 0; }
    assert(bytes==sizeof(*c) && c->cache_bytes==4096 && c->stripe_rows==8);
    return error;
}
int32_t x622_ui_scene(const x622_ui_node_t* n,uint32_t bytes,uint32_t duration) {
    assert(bytes==3*sizeof(*n) && bytes<=32*sizeof(*n));
    assert(duration<=500 && n[1].x>=40 && n[1].x+n[1].w<=216);
    ++calls; return error;
}
#include "../examples/native-ui/main.c"
int main(void) {
    levels=4; xapp_init(); xapp_event(1,3,0,40,0); assert(calls==1 && exits==0);
    levels=0; xapp_tick(100);
    for (unsigned i=0;i<100;i++) { xapp_event(1,i%2?1:2,0,40,0); }
    assert(calls==101);
    for (unsigned i=0;i<100;i++) xapp_tick(i*100);
    assert(calls==101);
    xapp_event(1,4,0,2000,0); assert(exits==0);
    xapp_event(1,3,0,2000,0); assert(exits==1);
    xapp_shutdown(); assert(releases==1);
    error=-4; xapp_init(); xapp_tick(100); xapp_event(1,3,0,40,0); assert(exits==2);
    return 0;
}
