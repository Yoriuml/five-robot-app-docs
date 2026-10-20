// Links actual local production renderer; only LCD surface/heap/clock are stubs.
#include "x622_xapp.h"
#include <esp_heap_caps.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
extern "C" {
int32_t xapp_startup_ready(void);
void sdk_test_set_root(const char*);void sdk_test_set_levels(int32_t);
unsigned sdk_test_reads();unsigned sdk_test_exits();
void x622_test_ui_tick(uint64_t);void x622_test_ui_set_clock(uint64_t);void x622_test_ui_cleanup();
void test_ui_reset();unsigned test_ui_transfers();unsigned test_ui_bytes();unsigned test_ui_min_y();unsigned test_ui_max_y();
uint16_t test_ui_pixel(unsigned,unsigned);void test_ui_ppm(const char*);
}
static uint64_t clock_ms;
static void tick(){x622_test_ui_set_clock(clock_ms);xapp_tick(clock_ms);x622_test_ui_tick(clock_ms);clock_ms+=20;}
static void sample(int raw){sdk_test_set_levels(raw);tick();tick();}
static uint64_t checksum(){uint64_t n=0;for(unsigned y=0;y<240;y++)for(unsigned x=0;x<240;x++)n=n*65599+test_ui_pixel(x,y);return n;}
int main(int argc,char**argv){
    assert(argc==3);sdk_test_set_root(argv[1]);sdk_test_set_levels(8);x622_test_ui_set_clock(0);
    xapp_init();assert(xapp_startup_ready()==1);tick();assert(test_ui_transfers()>0);
    uint64_t initial=checksum();assert(test_ui_pixel(0,0)!=test_ui_pixel(14,28));
    unsigned ink=0;for(unsigned y=24;y<46;y++)for(unsigned x=24;x<120;x++)if(test_ui_pixel(x,y)!=test_ui_pixel(14,28))ink++;
    assert(ink>50);test_ui_ppm(argv[2]);assert(sdk_test_reads()==4224);
    sample(0);
    for(unsigned i=0;i<100;i++){
        test_ui_reset();sample(i%2?1:2);sample(0);
        for(unsigned frame=0;frame<10;frame++)tick();
        assert(test_ui_transfers()>0&&test_ui_min_y()>=76&&test_ui_max_y()<=218);
        assert(sdk_test_reads()==4224); // animation/navigation never reloads text
    }
    assert(checksum()==initial); // even navigation count returns selection to zero
    test_ui_reset();for(unsigned i=0;i<100;i++)tick();assert(test_ui_transfers()==0);
    sample(4);assert(sdk_test_exits()==1);xapp_shutdown();x622_test_ui_cleanup();assert(ui_heap_live==0);
    std::puts("PASS production renderer + native C template: visible complete scene, 100 dirty-only moves, no resource reload, idle silence, cleanup. NOT final-WASM or hardware/audio validation.");
    return 0;
}
