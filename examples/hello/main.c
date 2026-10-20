#include "product_input.h"
static product_input_t keys;
static uint32_t selected,failed,greeting,ready,exiting;
static x622_gfx_command_t scene[3]={
    {.opcode=X622_GFX_FILL_RECT,.w=240,.h=240,.color=0x0861},
    {.opcode=X622_GFX_TEXT,.flags=X622_GFX_TEXT_CENTER,.x=120,.y=82,.color=0xffff,.arg0=2,.text="Hello Five"},
    {.opcode=X622_GFX_TEXT,.flags=X622_GFX_TEXT_CENTER,.x=120,.y=142,.color=0x632c,.arg0=2,.text="Exit APP"}
};
static void draw(unsigned full){
    scene[1].color=selected==0?(greeting?0x7fff:0xffff):0x632c;
    scene[2].color=selected==1?0x7fff:0x632c;
    if(x622_gfx_submit(scene,sizeof(scene),full?0:20,full?0:74,full?240:200,full?240:90)<0)failed=1;
}
static void leave(void){if(!exiting){exiting=1;ready=0;(void)x622_exit();}}
void xapp_init(void){
    product_input_reset(&keys);selected=failed=greeting=ready=exiting=0;
    draw(1);ready=!failed;
}
X622_EXPORT("xapp_startup_ready") int32_t xapp_startup_ready(void){return ready&&!exiting;}
void xapp_tick(uint64_t now){
    if(exiting)return;
    if(failed){leave();return;}
    if(product_input_poll(&keys,now)<0)return;
    if(keys.down&PRODUCT_BACK){leave();return;}
    uint32_t old=selected;
    if(product_repeat(&keys,PRODUCT_UP,now))selected=0;
    if(product_repeat(&keys,PRODUCT_DOWN,now))selected=1;
    if(keys.click&PRODUCT_CONFIRM){
        if(selected){leave();return;}
        greeting=!greeting;draw(0);
    }else if(selected!=old)draw(0);
}
void xapp_event(uint32_t t,uint32_t a,uint32_t p,uint32_t held,uint32_t mask){
    (void)t;(void)a;(void)p;(void)held;(void)mask; /* input is polled, not duplicated */
}
void xapp_shutdown(void){exiting=1;ready=0;}
