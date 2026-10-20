/* Native C application bridge. NOT execution of the final WASM package. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "x622_xapp.h"
static const char *resource_root;
static int32_t levels;
static unsigned reads,exits;
void sdk_test_set_root(const char *path){resource_root=path;}
void sdk_test_set_levels(int32_t value){levels=value;}
unsigned sdk_test_reads(void){return reads;}
unsigned sdk_test_exits(void){return exits;}
int32_t x622_input_state(void){return levels;}
int32_t x622_exit(void){exits++;return 0;}
static FILE *resource(const char *name,unsigned count){
    char path[1024];assert(count<64&&strlen(resource_root)+count+2<sizeof(path));
    snprintf(path,sizeof(path),"%s/%.*s",resource_root,count,name);FILE*f=fopen(path,"rb");assert(f);return f;
}
int32_t x622_resource_size(const char*name,uint32_t count){
    FILE*f=resource(name,count);fseek(f,0,SEEK_END);int bytes=ftell(f);fclose(f);return bytes;
}
int32_t x622_resource_read(const char*name,uint32_t count,uint32_t offset,void*out,uint32_t bytes){
    FILE*f=resource(name,count);fseek(f,offset,SEEK_SET);int got=fread(out,1,bytes,f);fclose(f);reads+=got;return got;
}
#include "../examples/native-ui/main.c"
