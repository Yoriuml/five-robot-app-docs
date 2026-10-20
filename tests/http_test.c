#include <assert.h>
#include <string.h>
#include "x622_xapp.h"
static int32_t network,request_error,poll_error,transport,status_code;
static unsigned draws,exits,requests,stops,starts,full_draws;
int32_t x622_input_state(void){return 0;}
int32_t x622_exit(void){++exits;return 0;}
int32_t x622_wifi_start(void){starts++;return 0;}
int32_t x622_wifi_stop(void){stops++;return 0;}
int32_t x622_wifi_status(int32_t*out,uint32_t n){assert(n==8);out[0]=network;return 8;}
int32_t x622_http_request_ex(const x622_http_request_ex_t*r,uint32_t n){
    assert(n==sizeof(*r)&&r->response_limit==1024&&r->timeout_ms==4000&&!r->bearer[0]);requests++;return request_error;
}
int32_t x622_http_poll_ex(void*out,uint32_t n){
    assert(n==1057);x622_http_result_ex_t r={0};r.phase=2;r.error=transport;r.http_status=status_code;r.flags=X622_HTTP_RESPONSE_COMPLETE;
    memcpy(out,&r,sizeof(r));((unsigned char*)out)[sizeof(r)]=0;return poll_error?poll_error:33;
}
int32_t x622_gfx_submit(const x622_gfx_command_t*c,uint32_t n,int32_t x,int32_t y,int32_t w,int32_t h){
    (void)c;assert(n==3*sizeof(*c)&&x>=0&&y>=0&&x+w<=240&&y+h<=240);if(w==240)full_draws++;draws++;return 0;
}
#include "../examples/http/main.c"
int main(void){
    network=2;xapp_init();assert(xapp_startup_ready()&&starts==0);xapp_tick(100);assert(starts==0);
    xapp_tick(200);assert(stopped&&requests==0&&starts==1);
    network=4;request_error=-7;xapp_init();xapp_tick(100);xapp_tick(200);assert(!phase);
    request_error=0;xapp_tick(300);assert(phase==1);status_code=200;xapp_tick(400);assert(stopped);
    unsigned old=draws;for(unsigned i=0;i<200;i++)xapp_tick(500+i*100);assert(draws==old);
    transport=-11;xapp_init();xapp_tick(100);xapp_tick(200);xapp_tick(300);assert(stopped);
    transport=0;poll_error=-14;xapp_init();xapp_tick(100);xapp_tick(200);xapp_tick(300);assert(stopped);
    poll_error=0;network=3;xapp_init();xapp_tick(100);xapp_tick(200);xapp_tick(15200);assert(stopped);
    xapp_shutdown();assert(stops==1);return 0;
}
