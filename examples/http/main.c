#include "x622_xapp.h"

static uint32_t armed, phase, stopped;
static uint64_t deadline, last_poll;
static int32_t wifi[2];
static int32_t response[516]; /* 12-byte status + <=2048 bytes + NUL, aligned */
static const x622_http_request_t request = {
    .method=0, .url="https://site.flashbot5.com/developer/v1/index.json"
};
static x622_gfx_command_t scene[3] = {
    { .opcode=X622_GFX_FILL_RECT, .w=240, .h=240, .color=0x0841 },
    { .opcode=X622_GFX_TEXT, .flags=1, .x=120, .y=80, .color=0x07ff, .arg0=2, .text="Connecting" },
    { .opcode=X622_GFX_TEXT, .flags=1, .x=120, .y=156, .color=0xffff, .arg0=2, .text="Exit APP" }
};
static void status(const char* text) {
    uint32_t i=0;
    while (text[i] && i<23) { scene[1].text[i]=text[i]; ++i; }
    scene[1].text[i]=0;
    if (x622_gfx_submit(scene,sizeof(scene),0,0,240,240)<0) stopped=1;
}
void xapp_init(void) {
    armed=phase=stopped=0; last_poll=0;
    deadline=x622_millis()+15000;
    status("Connecting");
    if (stopped) return;
    if (x622_wifi_start()<0) { stopped=1; status("Wi-Fi error"); }
}
void xapp_tick(uint64_t now) {
    if (!armed && x622_input_state()==0) armed=1;
    if (stopped || now-last_poll<100) return;
    last_poll=now;
    if (now>=deadline) { stopped=1; status("Timeout"); return; }
    if (!phase) {
        int32_t result=x622_wifi_status(wifi,sizeof(wifi));
        if (result<0) { stopped=1; status("Wi-Fi error"); return; }
        if (wifi[0]==X622_WIFI_CONFIG_PORTAL) { stopped=1; status("Set Wi-Fi first"); return; }
        if (wifi[0]!=X622_WIFI_CONNECTED) return;
        result=x622_http_request(&request,sizeof(request));
        if (result==X622_ERR_BUSY) return;
        if (result<0) { stopped=1; status("Request error"); return; }
        phase=1; status("Loading");
    } else {
        int32_t result=x622_http_poll(response,sizeof(response));
        if (result<0) { stopped=1; status("Network error"); return; }
        if (result>=12 && response[0]==2) {
            stopped=1;
            status(response[1]==0 && response[2]>=200 && response[2]<300 ? "Received" : "HTTP/TLS error");
        }
    }
}
void xapp_event(uint32_t type,uint32_t action,uint32_t event_phase,uint32_t held,uint32_t mask) {
    (void)event_phase; (void)mask;
    if (!armed || type!=1 || held>=600) return;
    if (action==X622_INPUT_CONFIRM) { (void)x622_exit(); return; }
}
void xapp_shutdown(void) { (void)x622_wifi_stop(); }
