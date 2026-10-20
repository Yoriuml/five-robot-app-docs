#include "product_input.h"
/* Packaged background is streamed by the host; no 115200-byte WASM buffer. */
static product_input_t keys;
static uint32_t selected,failed,ready,exiting;
static x622_gfx_command_t nodes[3]={
    {.opcode=X622_GFX_STROKE_RECT,.x=20,.y=20,.w=200,.h=200,.color=0x07ff,.arg0=2},
    {.opcode=X622_GFX_TEXT,.flags=X622_GFX_TEXT_CENTER,.x=120,.y=174,.color=0xffff,.arg0=2,.text="Exit APP"},
    {.opcode=X622_GFX_FILL_RECT,.x=104,.y=206,.w=32,.h=3,.color=0x07ff}
};
static void draw(unsigned full){
    nodes[1].color=selected?0x07ff:0x6b4d;
    if(x622_gfx_resource("hello.rgb565",12,nodes,sizeof(nodes),full?0:20,full?0:168,full?240:200,full?240:26)<0)failed=1;
}
static void leave(void){if(!exiting){exiting=1;ready=0;(void)x622_exit();}}
void xapp_init(void){product_input_reset(&keys);selected=failed=ready=exiting=0;draw(1);ready=!failed;}
X622_EXPORT("xapp_startup_ready") int32_t xapp_startup_ready(void){return ready&&!exiting;}
void xapp_tick(uint64_t now){
    if(exiting)return;if(failed){leave();return;}
    if(product_input_poll(&keys,now)<0)return;
    if(keys.down&PRODUCT_BACK){leave();return;}
    unsigned old=selected;
    if(product_repeat(&keys,PRODUCT_DOWN,now))selected=1;
    if(product_repeat(&keys,PRODUCT_UP,now))selected=0;
    if((keys.click&PRODUCT_CONFIRM)&&selected){leave();return;}
    if(old!=selected)draw(0);
}
void xapp_event(uint32_t t,uint32_t a,uint32_t p,uint32_t h,uint32_t m){(void)t;(void)a;(void)p;(void)h;(void)m;}
void xapp_shutdown(void){exiting=1;ready=0;}
