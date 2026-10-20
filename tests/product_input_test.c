#include <assert.h>
#include "../examples/native-ui/product_input.h"
static int32_t raw;
int32_t x622_input_state(void){return raw;}
static void poll(product_input_t*p,int32_t value,uint64_t now){raw=value;product_input_poll(p,now);product_input_poll(p,now+20);}
int main(void){
    product_input_t p;product_input_reset(&p);poll(&p,8,10);assert(!p.armed);poll(&p,0,40);assert(p.armed);
    assert(product_state_from_physical_mask(1)==PRODUCT_BACK);
    assert(product_state_from_physical_mask(2)==PRODUCT_CONFIRM);
    assert(product_state_from_physical_mask(4)==PRODUCT_DOWN);
    assert(product_state_from_physical_mask(8)==PRODUCT_UP);
    assert(product_role_from_event(X622_INPUT_CONFIRM)==PRODUCT_BACK);
    assert(product_role_from_event(X622_INPUT_BACK)==PRODUCT_CONFIRM);
    poll(&p,8,100);assert(p.down==8);
    assert(!product_take_long(&p,8,719,700));
    assert(product_take_long(&p,8,820,700));
    assert(!product_take_long(&p,8,900,700));
    poll(&p,0,940);assert(!(p.click&8));
    poll(&p,8,1000);poll(&p,0,1060);assert(p.click&8);
    raw=-5;assert(product_input_poll(&p,1100)==-5&&!p.down&&!p.up&&!p.click);
    poll(&p,1,1140);assert(!p.armed&&!p.down);poll(&p,0,1180);assert(p.armed);
    poll(&p,1,1220);assert(product_repeat(&p,1,1240));raw=1;product_input_poll(&p,9000);assert(product_repeat(&p,1,9000));
    assert(!product_repeat(&p,1,9000)); /* no catch-up bursts */
    return 0;
}
