#include "audio_pill.c"
#include <assert.h>
static GtkContainer *root(wbcffi_module *obj) { return GTK_CONTAINER(obj); }
static void spin(double seconds) {
    gint64 until=g_get_monotonic_time()+(gint64)(seconds*G_TIME_SPAN_SECOND);
    do { while(g_main_context_iteration(NULL,FALSE)) {} g_usleep(10000); }
    while(g_get_monotonic_time()<until);
}
int main(int argc,char **argv) {
    gtk_init(&argc,&argv);
    GtkWidget *a=gtk_offscreen_window_new(),*b=gtk_offscreen_window_new();
    Init ia={(wbcffi_module*)a,"0.15.0",root,NULL};
    Init ib={(wbcffi_module*)b,"0.15.0",root,NULL};
    Entry embedded={"embedded","true\n"};
    void *one=wbcffi_init(&ia,NULL,0),*two=wbcffi_init(&ib,&embedded,1);
    int width,height;
    gtk_widget_get_size_request(((Instance*)two)->area,&width,&height);
    assert(width==PILL_WIDTH && height==18 && ((Instance*)two)->embedded);
    gtk_widget_show_all(a); gtk_widget_show_all(b);
    spin(2);
    assert(g_list_length(instances)==2 && timer && capture && audio_fd>=0);
    GSubprocess *shared=capture;
    wbcffi_deinit(one); gtk_widget_destroy(a); spin(.5);
    assert(g_list_length(instances)==1 && capture==shared && timer);
    memset(frame,0,sizeof frame); analyze();
    for(int i=0;i<N;i++) assert(target[i]==0);
    for(int i=0;i<SAMPLES;i++) {
        int16_t s=(int16_t)(10000*sin(2*G_PI*600*i/RATE));
        frame[2*i]=(unsigned)s&255; frame[2*i+1]=((unsigned)s>>8)&255;
    }
    analyze(); double maximum=0;
    for(int i=0;i<N;i++) { assert(isfinite(target[i]) && target[i]>=0 && target[i]<=1); maximum=MAX(maximum,target[i]); }
    assert(maximum>.3);
    wbcffi_deinit(two); gtk_widget_destroy(b);
    assert(!instances && !timer && !capture && audio_fd<0);
    g_print("PASS: two widgets share capture; capture survives partial teardown; silence, tone response and final cleanup.\n");
    return 0;
}
