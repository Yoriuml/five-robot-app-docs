#include <assert.h>
#include <stdio.h>
#include "x622_xapp.h"
static unsigned draws,exits,full_draws;
static int32_t levels,error;
int32_t x622_input_state(void){return levels;}
int32_t x622_exit(void){++exits;return 0;}
int32_t x622_gfx_submit(const x622_gfx_command_t*c,uint32_t n,int32_t x,int32_t y,int32_t w,int32_t h){
    assert(n==3*sizeof(*c)&&x>=0&&y>=0&&x+w<=240&&y+h<=240);
    if(w==240&&h==240)full_draws++;draws++;return error;
}
#include "../examples/hello/main.c"
static void sample(int32_t raw,uint64_t at){levels=raw;xapp_tick(at);xapp_tick(at+20);}
int main(void){
    levels=8;xapp_init();assert(xapp_startup_ready()==1&&draws==1);
    xapp_event(1,3,0,40,1);assert(exits==0);sample(8,20);assert(!keys.armed);
    sample(0,60);assert(keys.armed);
    sample(2,100);assert(selected==1&&draws==2&&full_draws==1);
    sample(0,140);assert(draws==2);xapp_event(1,2,0,900,4);assert(draws==2);
    sample(8,180);sample(0,220);assert(exits==1&&draws==2);
    xapp_shutdown();assert(!xapp_startup_ready());
    error=-4;xapp_init();xapp_tick(300);assert(exits==2);
    puts("PASS native C state fixture: product buttons, release fence, dirty navigation, ready/error/exit");
    return 0;
}
