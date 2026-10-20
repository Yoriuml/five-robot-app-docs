#include <assert.h>
#include "x622_xapp.h"
static unsigned calls,exits,full_calls;static int32_t levels,error;
int32_t x622_input_state(void){return levels;}
int32_t x622_exit(void){exits++;return 0;}
int32_t x622_gfx_resource(const char*p,uint32_t pn,const x622_gfx_command_t*c,uint32_t n,int32_t x,int32_t y,int32_t w,int32_t h){
    (void)p;assert(pn==12&&n==3*sizeof(*c)&&x>=0&&y>=0&&x+w<=240&&y+h<=240);
    if(w==240&&h==240)full_calls++;calls++;return error;
}
#include "../examples/resources-zh/main.c"
static void sample(int raw,uint64_t now){levels=raw;xapp_tick(now);xapp_tick(now+20);}
int main(void){
    levels=8;xapp_init();sample(8,20);assert(calls==1&&xapp_startup_ready());
    sample(0,60);
    for(unsigned i=0;i<20;i++){sample(i%2?1:2,100+i*80);sample(0,140+i*80);}
    assert(calls==21&&full_calls==1);
    sample(4,2000);assert(exits==1);xapp_shutdown();
    error=-4;xapp_init();xapp_tick(2100);assert(exits==2);return 0;
}
