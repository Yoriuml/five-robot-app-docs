#include "product_input.h"

static product_input_t keys;
static unsigned ready, exiting, started, failed;
static int32_t displayed;
static uint64_t next_poll;
static x622_gfx_command_t scene[3] = {
    {.opcode=X622_GFX_FILL_RECT,.w=240,.h=240,.color=0x0861},
    {.opcode=X622_GFX_TEXT,.flags=X622_GFX_TEXT_CENTER,.x=120,.y=78,.color=0xffff,.arg0=2,.text="BLE session"},
    {.opcode=X622_GFX_TEXT,.flags=X622_GFX_TEXT_CENTER,.x=120,.y=130,.color=0x7fff,.arg0=1,.text="Middle: start / Left: exit"}
};
static void draw(int full) {
    if(x622_gfx_submit(scene,sizeof(scene),0,full?0:72,240,full?240:80)<0)failed=1;
}
static void label(const char *s) {
    unsigned i=0;
    for(;s[i]&&i<sizeof(scene[2].text)-1;++i)scene[2].text[i]=s[i];
    scene[2].text[i]=0;draw(0);
}
static void leave(void) {
    if(exiting)return;
    exiting=1;ready=0;
    (void)x622_ble_stop();started=0;
    (void)x622_exit();
}
void xapp_init(void) {
    product_input_reset(&keys);
    ready=exiting=started=failed=0;displayed=-999;next_poll=0;
    draw(1);ready=!failed; /* Complete offline frame before any service request. */
}
X622_EXPORT("xapp_startup_ready") int32_t xapp_startup_ready(void){return ready&&!exiting;}
void xapp_tick(uint64_t now) {
    if(exiting)return;
    if(failed){leave();return;}
    if(product_input_poll(&keys,now)<0)return;
    if(keys.down&PRODUCT_BACK){leave();return;}
    if(keys.click&PRODUCT_CONFIRM){
        if(started){
            int32_t error=x622_ble_stop();
            if(error<0){label("Stop failed; Left to exit");return;}
            started=0;label("Stopped; Middle to start");
        }else{
            x622_ble_config_t config={.version=X622_BLE_CONFIG_VERSION,.size=sizeof(config),
                .role=X622_BLE_ROLE_STREAM,.name="Five BLE#",
                .service_uuid={1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0xa1},
                .rx_uuid={2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0xa1},
                .tx_uuid={3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0xa1}};
            int32_t error=x622_ble_open(&config,sizeof(config));
            if(error<0){label(error==X622_ERR_BUSY?"Radio busy; Middle retries":"Start failed; Middle retries");return;}
            started=1;displayed=-999;next_poll=now;
        }
    }
    if(started&&now>=next_poll){
        next_poll=now+200;
        x622_ble_status_t status;
        int32_t error=x622_ble_status(&status,sizeof(status));
        int32_t state=error<0?error:status.state;
        if(state!=displayed){
            displayed=state;
            label(state<0?"Status failed; Left to exit":state==3?"Connected and ready":
                  state==4?"Pair on receiving device":state==2?"Connected; subscribe TX":"Advertising; Middle stops");
        }
    }
}
void xapp_event(uint32_t a,uint32_t b,uint32_t c,uint32_t d,uint32_t e){
    (void)a;(void)b;(void)c;(void)d;(void)e; /* One input source, no duplicate events. */
}
void xapp_shutdown(void){(void)x622_ble_stop();started=ready=0;exiting=1;}
