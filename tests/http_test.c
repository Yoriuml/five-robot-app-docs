#include <assert.h>
#include "x622_xapp.h"
static int32_t network,request_error,poll_error,transport,status_code;
static unsigned draws,exits,requests,stops;
int32_t x622_input_state(void) { return 0; }
int32_t x622_exit(void) { ++exits; return 0; }
uint64_t x622_millis(void) { return 0; }
int32_t x622_wifi_start(void) { return 0; }
int32_t x622_wifi_stop(void) { ++stops; return 0; }
int32_t x622_wifi_status(int32_t* out,uint32_t bytes) { assert(bytes==8); out[0]=network; return 8; }
int32_t x622_http_request(const x622_http_request_t* req,uint32_t bytes) {
    assert(bytes==sizeof(*req) && req->method==0 && !req->bearer[0]); ++requests; return request_error;
}
int32_t x622_http_poll(void* out,uint32_t bytes) {
    assert(bytes>=2061); int32_t* head=out; head[0]=2; head[1]=transport; head[2]=status_code;
    return poll_error ? poll_error : 12;
}
int32_t x622_gfx_submit(const x622_gfx_command_t* c,uint32_t bytes,int32_t x,int32_t y,int32_t w,int32_t h) {
    (void)c;(void)x;(void)y; assert(bytes==3*sizeof(*c) && w==240 && h==240); ++draws; return 0;
}
#include "../examples/http/main.c"
int main(void) {
    network=2; xapp_init(); xapp_tick(100); assert(stopped && requests==0);
    xapp_event(1,3,0,40,0); assert(exits==1);
    network=4; request_error=-7; xapp_init(); xapp_tick(100); assert(!phase);
    request_error=0; xapp_tick(200); assert(phase==1);
    status_code=200; xapp_tick(300); assert(stopped);
    unsigned old=draws; for (unsigned i=0;i<200;i++) xapp_tick(400+i*100); assert(draws==old);
    transport=-11; xapp_init(); xapp_tick(100); xapp_tick(200); assert(stopped);
    poll_error=-14; xapp_init(); xapp_tick(100); xapp_tick(200); assert(stopped);
    network=3; xapp_init(); xapp_tick(15000); assert(stopped);
    xapp_shutdown(); assert(stops==1); return 0;
}
