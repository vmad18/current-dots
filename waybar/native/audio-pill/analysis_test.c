#include "audio_pill.c"
#include <assert.h>
static void tone(double hz,double amplitude) {
    for (int i=0;i<SAMPLES;i++) {
        int16_t value=(int16_t)lround(32767*amplitude*sin(2*G_PI*hz*i/RATE));
        frame[2*i]=(unsigned)value&255;
        frame[2*i+1]=((unsigned)value>>8)&255;
    }
    analyze();
}
static int tallest(void) {
    int j=0;
    for(int i=0;i<N;i++) { assert(isfinite(target[i]) && target[i]>=0 && target[i]<=1); if(target[i]>target[j]) j=i; }
    return j;
}
int main(void) {
    prepare_analysis();
    assert(bin_start[0]>=1 && bin_end[N-1]<=SAMPLES/2);
    for(int i=1;i<N;i++) assert(bin_start[i]==bin_end[i-1]);
    memset(frame,0,sizeof frame); analyze();
    assert(target_brightness==0);
    for(int i=0;i<N;i++) assert(target[i]==0);

    double heights[3]; int chosen[3];
    const double frequencies[]={70,1000,12000};
    for(int k=0;k<3;k++) {
        tone(frequencies[k],.20);
        chosen[k]=tallest(); heights[k]=target[chosen[k]];
        double bin=frequencies[k]*SAMPLES/RATE;
        assert(bin>=bin_start[chosen[k]]-1 && bin<=bin_end[chosen[k]]+1);
        assert(heights[k]>.65 && heights[k]<.88);
        g_print("tone %.0f Hz: bar %d, height %.3f, brightness %.3f\n",
                frequencies[k],chosen[k],heights[k],target_brightness);
    }
    assert(chosen[0]<chosen[1] && chosen[1]<chosen[2]);
    assert(fabs(heights[0]-heights[1])<.08 && fabs(heights[1]-heights[2])<.08);

    tone(1000,.20); double loud=target[tallest()], light=target_brightness;
    tone(1000,.02); double quiet=target[tallest()], dim=target_brightness;
    assert(fabs((loud-quiet)-20.0/(DB_CEILING-DB_FLOOR))<.005);
    assert(fabs((light-dim)-20.0/(DB_CEILING-DB_FLOOR))<.005);
    double reference[N]; memcpy(reference,target,sizeof reference);
    tone(1000,.90); tone(1000,.02);
    for(int i=0;i<N;i++) assert(fabs(reference[i]-target[i])<1e-12);

    /* Simultaneous bass and treble should remain independently represented. */
    for(int i=0;i<SAMPLES;i++) {
        double v=.15*sin(2*G_PI*70*i/RATE)+.15*sin(2*G_PI*12000*i/RATE);
        int16_t s=(int16_t)lround(32767*v);
        frame[2*i]=(unsigned)s&255; frame[2*i+1]=((unsigned)s>>8)&255;
    }
    analyze();
    assert(target[chosen[0]]>.55 && target[chosen[2]]>.55);
    gint64 start=g_get_monotonic_time();
    for(int n=0;n<1000;n++) analyze();
    double micros=(g_get_monotonic_time()-start)/1000.0;
    g_print("PASS: frequency coverage, 20 dB amplitude separation, brightness, no gain history, mixed tones.\n");
    g_print("Analysis benchmark: %.1f us/frame; %.2f%% of one core at %.2f frames/s (analysis only).\n",
        micros,micros*(RATE/(double)HOP)/10000.0,RATE/(double)HOP);
    return 0;
}
