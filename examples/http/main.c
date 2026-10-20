#include "product_input.h"
static product_input_t keys;
static uint32_t phase,stopped,failed,ready,exiting,present_ticks;
static uint64_t deadline,last_poll;
static int32_t wifi[2];
static uint8_t response[1057]; /* exact 32-byte header + 1024 payload + NUL */
static const x622_http_request_ex_t request={
    .method=0,.response_limit=1024,.timeout_ms=4000,
    .url="https://site.flashbot5.com/developer/v1/index.json"
};
static x622_gfx_command_t scene[3]={
    {.opcode=X622_GFX_FILL_RECT,.w=240,.h=240,.color=0x0841},
    {.opcode=X622_GFX_TEXT,.flags=1,.x=120,.y=80,.color=0x07ff,.arg0=2,.text="Connecting"},
    {.opcode=X622_GFX_TEXT,.flags=1,.x=120,.y=156,.color=0xffff,.arg0=2,.text="Left: back"}
};
static void status(const char *text,unsigned full){
    uint32_t i=0;while(text[i]&&i<23){scene[1].text[i]=text[i];++i;}scene[1].text[i]=0;
    if(x622_gfx_submit(scene,sizeof(scene),full?0:16,full?0:70,full?240:208,full?240:38)<0)failed=1;
}
static void leave(void){if(!exiting){exiting=1;ready=0;(void)x622_exit();}}
void xapp_init(void){
    product_input_reset(&keys);phase=stopped=failed=ready=exiting=present_ticks=0;deadline=last_poll=0;
    status("Connecting",1);ready=!failed;
}
X622_EXPORT("xapp_startup_ready") int32_t xapp_startup_ready(void){return ready&&!exiting;}
void xapp_tick(uint64_t now){
    if(exiting)return;if(failed){leave();return;}
    (void)product_input_poll(&keys,now);
    if(keys.down&PRODUCT_BACK){leave();return;}
    if(++present_ticks<2||stopped)return;
    if(!deadline){
        deadline=now+15000;
        if(x622_wifi_start()<0){stopped=1;status("Wi-Fi error",0);return;}
    }
    if(now-last_poll<100)return;last_poll=now;
    if(now>=deadline){stopped=1;status("Timeout",0);return;}
    if(!phase){
        int32_t result=x622_wifi_status(wifi,sizeof(wifi));
        if(result!=sizeof(wifi)){stopped=1;status("Wi-Fi error",0);return;}
        if(wifi[0]==X622_WIFI_CONFIG_PORTAL){stopped=1;status("Set Wi-Fi first",0);return;}
        if(wifi[0]!=X622_WIFI_CONNECTED)return;
        result=x622_http_request_ex(&request,sizeof(request));
        if(result==X622_ERR_BUSY)return;
        if(result<0){stopped=1;status("Request error",0);return;}
        phase=1;status("Loading",0);
    }else{
        int32_t bytes=x622_http_poll_ex(response,sizeof(response));
        if(bytes<0){stopped=1;status("Network error",0);return;}
        if(bytes>=sizeof(x622_http_result_ex_t)){
            x622_http_result_ex_t result;
            unsigned char *out=(unsigned char*)&result;
            for(unsigned i=0;i<sizeof(result);i++)out[i]=response[i];
            if(result.phase==2){
                stopped=1;
                int okay=result.error==0&&result.http_status>=200&&result.http_status<300&&
                    (result.flags&X622_HTTP_RESPONSE_COMPLETE)&&result.response_bytes<=1024&&
                    bytes>=sizeof(result)+result.response_bytes+1&&response[sizeof(result)+result.response_bytes]==0;
                status(okay?"Received":"HTTP/body error",0);
            }
        }
    }
}
void xapp_event(uint32_t t,uint32_t a,uint32_t p,uint32_t h,uint32_t m){(void)t;(void)a;(void)p;(void)h;(void)m;}
void xapp_shutdown(void){exiting=1;ready=0;(void)x622_wifi_stop();}
