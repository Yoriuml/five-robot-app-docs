#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "x622_xapp.h"
static int32_t levels,error,resource_error,audio_error;
static unsigned calls,exits,releases,textures,tracks[2],stops,status_calls;
static const char *resource_root;
int32_t x622_input_state(void){return levels;}
int32_t x622_exit(void){exits++;return 0;}
int32_t x622_ui_config(const x622_ui_config_t*c,uint32_t n){
    if(!n){releases++;return 0;}
    assert(n==sizeof(*c)&&c->cache_bytes==8192&&c->stripe_rows==8);return error;
}
int32_t x622_ui_texture(uint32_t slot,uint32_t kind,int32_t w,int32_t h,const void*p,uint32_t n){
    assert(slot<4&&kind==X622_UI_MASK_A4&&w==96&&h==22&&n==1056);
    unsigned ink=0;for(unsigned i=0;i<n;i++)ink|=((const unsigned char*)p)[i];assert(ink);textures++;return error;
}
int32_t x622_ui_scene(const x622_ui_node_t*n,uint32_t bytes,uint32_t duration){
    assert(bytes==9*sizeof(*n)&&duration<=500);
    for(unsigned i=0;i<9;i++){
        assert(n[i].opacity==255&&n[i].clip_w==240&&n[i].clip_h==240&&n[i].w>0&&n[i].h>0);
        for(unsigned j=0;j<i;j++)assert(n[i].id!=n[j].id);
    }calls++;return error;
}
static FILE *open_resource(const char*p,unsigned n){
    char path[1024];assert(n<64&&strlen(resource_root)+n+2<sizeof(path));
    snprintf(path,sizeof(path),"%s/%.*s",resource_root,n,p);return fopen(path,"rb");
}
int32_t x622_resource_size(const char*p,uint32_t n){
    if(resource_error)return -6;FILE*f=open_resource(p,n);assert(f);fseek(f,0,SEEK_END);int size=ftell(f);fclose(f);return size;
}
int32_t x622_resource_read(const char*p,uint32_t n,uint32_t offset,void*out,uint32_t bytes){
    if(resource_error)return -6;FILE*f=open_resource(p,n);assert(f);fseek(f,offset,SEEK_SET);int count=fread(out,1,bytes,f);fclose(f);return count;
}
int32_t x622_audio_track(const x622_audio_track_t*c,uint32_t n){
    assert(n==sizeof(*c)&&c->voice<2);
    if(c->operation==X622_AUDIO_TRACK_STOP){stops++;return 0;}
    assert(c->sample_rate==16000&&c->bytes>0&&!(c->bytes&1)&&c->gain_q8<=256);
    tracks[c->voice]++;return audio_error;
}
int32_t x622_audio_mix_status(x622_audio_mix_status_t*out,uint32_t n){
    assert(n==sizeof(*out));*out=(x622_audio_mix_status_t){0};status_calls++;return n;
}
int32_t x622_audio_stop(void){stops++;return 0;}
#ifdef AUDIO_TEST
#include "../examples/native-ui-audio/main.c"
#else
#include "../examples/native-ui/main.c"
#endif
static void sample(int raw,uint64_t now){levels=raw;xapp_tick(now);xapp_tick(now+20);}
int main(int argc,char**argv){
    assert(argc==2);resource_root=argv[1];levels=8;xapp_init();
    assert(calls==1&&textures==4&&xapp_startup_ready()==1);
    assert(xapp_startup_ready()==1&&tracks[0]==0);
    xapp_tick(0);assert(tracks[0]==0);xapp_tick(20);
#ifdef AUDIO_TEST
    assert(tracks[0]==1);
#endif
    sample(8,40);assert(!keys.armed);sample(0,80);assert(keys.armed);
    unsigned old=calls;sample(2,120);assert(selected==1&&calls==old+1);
    sample(0,160);old=calls;
    xapp_event(1,2,0,900,4);assert(calls==old);
    sample(8,200);assert(calls==old);sample(0,240);assert(calls>=old+1);
#ifdef AUDIO_TEST
    assert(tracks[1]==1&&tracks[0]==1); /* effect never restarts background */
#endif
    old=calls;for(unsigned i=0;i<100;i++)xapp_tick(300+i*20);assert(calls==old);
    sample(4,3000);assert(exits==1&&!xapp_startup_ready());xapp_shutdown();assert(releases==1);
    error=-4;xapp_init();assert(!xapp_startup_ready());xapp_tick(4000);assert(exits==2);xapp_shutdown();
    error=0;resource_error=1;xapp_init();xapp_tick(4100);assert(exits==3);xapp_shutdown();
    puts("PASS native C contract fixture (not rendering/audio hardware): A4/resources/buttons/first-frame barrier/error/exit");
    return 0;
}
