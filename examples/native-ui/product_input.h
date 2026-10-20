/* Product roles over the unchanged historical ABI. CC0-1.0 SDK example helper.
 * Poll ONE input source. Do not feed event.pressed_mask into this function.
 * input_state: up=1/down=2/left=4/middle=8; event mask is K1..K4 instead. */
#ifndef FIVE_PRODUCT_INPUT_H
#define FIVE_PRODUCT_INPUT_H
#include "x622_xapp.h"
#define PRODUCT_UP 1u
#define PRODUCT_DOWN 2u
#define PRODUCT_BACK 4u
#define PRODUCT_CONFIRM 8u
typedef struct {
    uint32_t armed,candidate,held,down,up,click,consumed;
    uint64_t candidate_at,since[4],repeat_at[2];
} product_input_t;
static void product_input_reset(product_input_t *p) { *p=(product_input_t){0}; }
static uint32_t product_state_from_physical_mask(uint32_t mask) {
    return ((mask&8)>>3)|((mask&4)>>1)|((mask&1)<<2)|((mask&2)<<2);
}
static uint32_t product_role_from_event(uint32_t action) {
    return action==X622_INPUT_UP?PRODUCT_UP:action==X622_INPUT_DOWN?PRODUCT_DOWN:
        action==X622_INPUT_CONFIRM?PRODUCT_BACK:action==X622_INPUT_BACK?PRODUCT_CONFIRM:0;
}
static int32_t product_input_poll(product_input_t *p,uint64_t now) {
    int32_t value=x622_input_state();p->down=p->up=p->click=0;
    if(value<0){product_input_reset(p);p->candidate_at=now;return value;}
    uint32_t raw=(uint32_t)value&15;
    if(raw!=p->candidate){p->candidate=raw;p->candidate_at=now;return 0;}
    if(now-p->candidate_at<15)return 0;
    if(!p->armed){if(!raw){p->armed=1;p->held=0;}return 0;}
    p->down=raw&~p->held;p->up=p->held&~raw;
    for(unsigned i=0;i<4;i++){
        uint32_t bit=1u<<i;
        if(p->down&bit){p->since[i]=now;p->consumed&=~bit;}
        if((p->up&bit)&&!(p->consumed&bit)&&now-p->since[i]<700)p->click|=bit;
    }
    p->consumed&=~p->up;p->held=raw;return 0;
}
static int product_take_long(product_input_t *p,unsigned bit,uint64_t now,uint32_t threshold) {
    unsigned index=bit==1?0:bit==2?1:bit==4?2:3;
    if((p->held&bit)&&!(p->consumed&bit)&&now-p->since[index]>=threshold){
        p->consumed|=bit;return 1;
    }return 0;
}
static int product_repeat(product_input_t *p,unsigned bit,uint64_t now) {
    unsigned index=bit==PRODUCT_DOWN;
    if(p->down&bit){p->repeat_at[index]=now+320;return 1;}
    if(!(p->held&bit)){p->repeat_at[index]=0;return 0;}
    if(p->repeat_at[index]&&now>=p->repeat_at[index]){
        uint64_t age=now-p->since[index];
        p->repeat_at[index]=now+(age>1200?80:age>700?110:150);return 1;
    }return 0;
}
#endif
