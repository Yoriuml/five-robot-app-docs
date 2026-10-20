#define PRODUCT_AUDIO_DEMO 1
/* Complete retained scene; no direct gfx calls while UI owns the surface. */
#include "product_input.h"
static product_input_t keys;
static uint32_t selected,failed,exiting,ready,present_ticks,shift,accent;
static uint8_t mask[1056];
static x622_ui_node_t scene_nodes[10];
#ifdef PRODUCT_AUDIO_DEMO
static uint32_t music_wanted=1,music_sent,audio_failed,attempts;
static uint64_t audio_retry,poll_at;
static int32_t music_size,effect_size;
static int32_t submit_track(unsigned voice,unsigned play) {
    x622_audio_track_t command={0};command.voice=voice;command.operation=play;
    if(play){
        const char *name=voice?"effect.pcm":"music.pcm";unsigned i=0;
        do {command.resource[i]=name[i];}while(name[i++]);
        command.bytes=voice?effect_size:music_size;command.sample_rate=16000;
        command.gain_q8=192;command.priority=voice?128:32;command.duck_q8=voice?96:256;
        command.flags=voice?0:X622_AUDIO_TRACK_LOOP;
    }
    return x622_audio_track(&command,sizeof(command));
}
#endif
static void publish(uint32_t duration) {
    unsigned count=0;
    for(unsigned i=0;i<9;i++)scene_nodes[i]=(x622_ui_node_t){0};
    x622_ui_node_t *n=&scene_nodes[count++];n->id=1;n->kind=X622_UI_RECT;
    n->x=12;n->y=14;n->w=216;n->h=44;n->radius=12;n->color=0x18e3;
    n=&scene_nodes[count++];n->id=2;n->kind=X622_UI_MASK_A4;
    n->x=24;n->y=24;n->w=96;n->h=22;n->texture=0;n->color=0xffff;
    for(unsigned row=0;row<3;row++){
        n=&scene_nodes[count++];n->id=3+row;n->kind=X622_UI_RECT;
        n->x=12+(shift&&row==selected?8:0);n->y=76+row*50;n->w=216-(shift&&row==selected?8:0);
        n->h=42;n->radius=10;n->color=row==selected?(accent?0x7b5f:0x1b79):0x10a3;
        n=&scene_nodes[count++];n->id=6+row;n->kind=X622_UI_MASK_A4;
        n->x=30+(shift&&row==selected?8:0);n->y=86+row*50;n->w=96;n->h=22;n->texture=row+1;n->color=0xffff;
    }
    n=&scene_nodes[count++];n->id=9;n->kind=X622_UI_RECT;
    n->x=18;n->y=87+selected*50;n->w=4;n->h=20;n->radius=2;n->color=0x07ff;
#ifdef PRODUCT_AUDIO_DEMO
    n->color=audio_failed?0xf980:music_sent?0x07ee:0x07ff;
#endif
    for(unsigned i=0;i<count;i++){scene_nodes[i].clip_w=240;scene_nodes[i].clip_h=240;scene_nodes[i].opacity=255;}
    if(x622_ui_scene(scene_nodes,count*sizeof(scene_nodes[0]),duration)<0)failed=1;
}
static void leave(void){if(!exiting){exiting=1;ready=0;(void)x622_exit();}}
void xapp_init(void) {
    product_input_reset(&keys);selected=failed=exiting=ready=present_ticks=shift=accent=0;
#ifdef PRODUCT_AUDIO_DEMO
    music_wanted=1;music_sent=audio_failed=attempts=0;audio_retry=poll_at=0;
    music_size=x622_resource_size("music.pcm",9);effect_size=x622_resource_size("effect.pcm",10);
    if(music_size<=0||effect_size<=0||(music_size&1)||(effect_size&1))audio_failed=1;
#endif
    const x622_ui_config_t config={sizeof(config),1,0x0841,20,8192,8,0};
    if(x622_ui_config(&config,sizeof(config))<0){failed=1;return;}
    if(x622_resource_size("ui.a4",5)!=4224){failed=1;return;}
    for(unsigned slot=0;slot<4;slot++){
        if(x622_resource_read("ui.a4",5,slot*sizeof(mask),mask,sizeof(mask))!=sizeof(mask)||
           x622_ui_texture(slot,X622_UI_MASK_A4,96,22,mask,sizeof(mask))<0){failed=1;return;}
    }
    publish(0);ready=!failed;
}
X622_EXPORT("xapp_startup_ready") int32_t xapp_startup_ready(void){return ready&&!exiting;}
void xapp_tick(uint64_t now) {
    if(exiting)return;
    if(failed){leave();return;}
    if(product_input_poll(&keys,now)<0)return;
    if(keys.down&PRODUCT_BACK){leave();return;}
    unsigned old=selected;
    if(product_repeat(&keys,PRODUCT_UP,now)&&selected)selected--;
    if(product_repeat(&keys,PRODUCT_DOWN,now)&&selected<2)selected++;
    if(selected!=old){publish(160);if(failed){leave();return;}}
    if(keys.click&PRODUCT_CONFIRM){
        if(selected==2){leave();return;}
#ifdef PRODUCT_AUDIO_DEMO
        if(selected==0){
            music_wanted=!music_wanted;audio_failed=attempts=0;
            if(!music_wanted){if(submit_track(0,0)<0)audio_failed=1;music_sent=0;}
        }else if(effect_size>0&&submit_track(1,1)<0)audio_failed=1;
#else
        if(selected==0)accent=!accent;else shift=!shift;
#endif
        publish(160);
        if(failed){leave();return;}
    }
#ifdef PRODUCT_AUDIO_DEMO
    /* First tick precedes the host commit. Local audio starts on the NEXT tick. */
    if(++present_ticks<2)return;
    if(music_wanted&&!music_sent&&!audio_failed&&now>=audio_retry){
        int32_t result=submit_track(0,1);
        if(result>=0){music_sent=1;publish(0);}
        else if(result==X622_ERR_BUSY&&++attempts<4)audio_retry=now+250;
        else {audio_failed=1;publish(0);}
        if(failed){leave();return;}
    }
    if(now>=poll_at){
        x622_audio_mix_status_t status;poll_at=now+100;
        int32_t got=x622_audio_mix_status(&status,sizeof(status));
        if(got<0||(got==sizeof(status)&&status.state==3)){
            if(!audio_failed){audio_failed=1;publish(0);}
        }
    }
#endif
}
void xapp_event(uint32_t type,uint32_t action,uint32_t phase,uint32_t held,uint32_t physical_mask){
    (void)type;(void)action;(void)phase;(void)held;(void)physical_mask;
    /* Poll exactly once above. Events must not repeat the same gesture. */
}
void xapp_shutdown(void){
    exiting=1;ready=0;
#ifdef PRODUCT_AUDIO_DEMO
    (void)x622_audio_stop();music_sent=0;
#endif
    (void)x622_ui_config(0,0);
}
