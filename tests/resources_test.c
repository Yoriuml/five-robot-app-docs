#include <assert.h>
#include "x622_xapp.h"
static unsigned calls,exits;
static int32_t levels,error;
int32_t x622_input_state(void) { return levels; }
int32_t x622_exit(void) { ++exits; return 0; }
int32_t x622_gfx_resource(const char* p,uint32_t pbytes,const x622_gfx_command_t* c,uint32_t bytes,
                         int32_t x,int32_t y,int32_t w,int32_t h) {
    (void)p; (void)x; (void)y;
    assert(pbytes==12 && bytes==3*sizeof(*c) && w==240 && h==240);
    ++calls; return error;
}
#include "../examples/resources-zh/main.c"
int main(void) {
    levels=4; xapp_init(); xapp_event(1,2,0,40,0); assert(calls==1);
    levels=0; xapp_tick(100);
    for (unsigned i=0;i<20;i++) xapp_event(1,i%2?1:2,0,40,0);
    assert(calls==21);
    xapp_event(1,2,0,40,0); xapp_event(1,3,0,40,0); assert(exits==1);
    error=-4; xapp_init(); xapp_tick(200); xapp_event(1,3,0,40,0); assert(exits==2);
    return 0;
}
