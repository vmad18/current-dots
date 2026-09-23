/* Native Cairo audio pill; preview and Waybar CFFI use the same renderer.
 * Build/run instructions are in README.md beside this file.
 */
#include <gtk/gtk.h>
#include <gio/gunixinputstream.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <complex.h>
#include <string.h>

#define N 23
#define SAMPLES 4096
#define RATE 48000
#define HOP (SAMPLES/2)
#define DB_FLOOR (-60.0)
#define DB_CEILING (-6.0)
#define PILL_WIDTH 97

static void pill(cairo_t *cr, double x, double y, double w, double h) {
    double r = MIN(9.0, MIN(w,h)/2);
    cairo_new_sub_path(cr);
    cairo_arc(cr, x+w-r, y+r, r, -G_PI/2, 0);
    cairo_arc(cr, x+w-r, y+h-r, r, 0, G_PI/2);
    cairo_arc(cr, x+r, y+h-r, r, G_PI/2, G_PI);
    cairo_arc(cr, x+r, y+r, r, G_PI, 3*G_PI/2);
    cairo_close_path(cr);
}

static void paint(cairo_t *cr, double w, double h, const double *levels, gboolean embedded, double brightness) {
    double ph = embedded ? h : 28, y = (h-ph)/2;
    if (!embedded) {
    /* Same geometry; translucent ring and fill match the surrounding islands.
     * Cut the center out of the rim so it does not darken the fill underneath.
     */
    pill(cr, 0, y, w, ph);
    pill(cr, 4, y+3, w-8, ph-6);
    cairo_set_fill_rule(cr, CAIRO_FILL_RULE_EVEN_ODD);
    cairo_set_source_rgba(cr, 0, 0, 0, .40);
    cairo_fill(cr);
    cairo_set_fill_rule(cr, CAIRO_FILL_RULE_WINDING);
    pill(cr, 4, y+3, w-8, ph-6);
    /* Island grey rgba(150,150,150,.25), with its .8 widget opacity. */
    cairo_set_source_rgba(cr,150/255.0,150/255.0,150/255.0,.20);
    cairo_fill(cr);
    } else {
        /* Translucent brown lets the existing Waybar layer blur show through. */
        pill(cr,1.5,1.5,w-3,h-3);
        cairo_set_source_rgba(cr,48/255.0,39/255.0,34/255.0,.40);
        cairo_fill(cr);
    }
    /* Quiet dots and rounded strokes have identical centers and spacing. */
    for (int i=0; i<N; i++) {
        double v = CLAMP(levels[i],0,1);
        double bh = 1.5 + 7.0*v;
        double inset = w * (22.0/180.0);
        double x = inset + i*(w-2*inset)/(N-1);
        double cy = y+ph/2;
        cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
        cairo_set_line_width(cr, 1.55);
        cairo_move_to(cr,x,cy-(bh-1.55)/2);
        cairo_line_to(cr,x,cy+(bh-1.55)/2);
        /* Restrained neon halo, with a crisp orange core. */
        cairo_set_line_width(cr,3.0);
        cairo_set_source_rgba(cr,1,.45,.08,.02+.16*brightness*(.25+.75*v));
        cairo_stroke_preserve(cr);
        cairo_set_line_width(cr,1.55);
        cairo_set_source_rgba(cr,1,.52+.08*v,.12,.42+.55*brightness);
        cairo_stroke(cr);
    }
}

#ifdef AUDIO_PREVIEW
int main(int argc, char **argv) {
    if (argc!=2) return 2;
    const double active[N]={0,0,.05,0,.12,.21,.08,.38,.30,.58,.84,.47,
                            .96,.66,.28,.20,.08,0,.10,0,0,0,0};
    double quiet[N]={0};
    cairo_surface_t *s=cairo_image_surface_create(CAIRO_FORMAT_ARGB32,600,178);
    cairo_t *cr=cairo_create(s);
    cairo_set_source_rgb(cr,.075,.083,.098); cairo_paint(cr);
    cairo_select_font_face(cr,"sans",CAIRO_FONT_SLANT_NORMAL,CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(cr,12); cairo_set_source_rgb(cr,.72,.77,.83);
    cairo_move_to(cr,20,18); cairo_show_text(cr,"ACTIVE — actual size");
    cairo_move_to(cr,320,18); cairo_show_text(cr,"QUIET — actual size");
    cairo_save(cr); cairo_translate(cr,20,28); paint(cr,PILL_WIDTH,28,active,FALSE,.75); cairo_restore(cr);
    cairo_save(cr); cairo_translate(cr,320,28); paint(cr,PILL_WIDTH,28,quiet,FALSE,0); cairo_restore(cr);
    cairo_set_source_rgb(cr,.72,.77,.83); cairo_move_to(cr,20,81);
    cairo_show_text(cr,"3× detail — same renderer, illustrative audio levels");
    cairo_save(cr); cairo_translate(cr,20,89); cairo_scale(cr,3,3);
    paint(cr,PILL_WIDTH,28,active,FALSE,.75); cairo_restore(cr);
    cairo_status_t status=cairo_surface_write_to_png(s,argv[1]);
    cairo_destroy(cr); cairo_surface_destroy(s);
    return status==CAIRO_STATUS_SUCCESS?0:1;
}
#else
/* Waybar CFFI v2 ABI; verified against the installed Waybar 0.15.0 source. */
typedef struct wbcffi_module wbcffi_module;
typedef struct {
    wbcffi_module *obj;
    const char *waybar_version;
    GtkContainer *(*get_root_widget)(wbcffi_module *);
    void (*queue_update)(wbcffi_module *);
} Init;
typedef struct { const char *key; const char *value; } Entry;
const size_t wbcffi_version=2;

typedef struct { GtkWidget *area; gulong draw_handler; gboolean embedded; } Instance;
/* A single capture and timer serve both monitors. GTK owns all callbacks. */
static GList *instances;
static GSubprocess *capture;
static int audio_fd=-1;
static guint timer;
static gint64 retry_at;
static unsigned char frame[SAMPLES*2];
static size_t have;
static double levels[N], target[N], window[SAMPLES], window_energy;
static double brightness, target_brightness;
static int bin_start[N], bin_end[N];

static double db_level(double rms) {
    double db=20*log10(MAX(rms,1e-9));
    return CLAMP((db-DB_FLOOR)/(DB_CEILING-DB_FLOOR),0,1);
}
static void prepare_analysis(void) {
    window_energy=0;
    for (int i=0;i<SAMPLES;i++) {
        window[i]=.5-.5*cos(2*G_PI*i/(SAMPLES-1));
        window_energy+=window[i]*window[i];
    }
    for (int i=0;i<N;i++) {
        double low=40*pow(18000.0/40,i/(double)N);
        double high=40*pow(18000.0/40,(i+1)/(double)N);
        bin_start[i]=MAX(1,(int)lround(low*SAMPLES/RATE));
        bin_end[i]=MIN(SAMPLES/2,MAX(bin_start[i]+1,(int)lround(high*SAMPLES/RATE)));
    }
}

static void close_capture(void) {
    if (capture) {
        g_subprocess_force_exit(capture);
        g_subprocess_wait(capture,NULL,NULL);
        g_clear_object(&capture);
    }
    audio_fd=-1; have=0;
    retry_at=g_get_monotonic_time()+2*G_TIME_SPAN_SECOND;
}
static void open_capture(void) {
    if (g_get_monotonic_time()<retry_at) return;
    GError *error=NULL;
    capture=g_subprocess_new(G_SUBPROCESS_FLAGS_STDOUT_PIPE |
        G_SUBPROCESS_FLAGS_STDERR_SILENCE,&error,
        "parec","-d","@DEFAULT_MONITOR@","--format=s16le",
        "--channels=1","--rate=48000","--latency-msec=50",NULL);
    if (!capture) {
        g_clear_error(&error);
        retry_at=g_get_monotonic_time()+2*G_TIME_SPAN_SECOND;
        return;
    }
    GInputStream *stream=g_subprocess_get_stdout_pipe(capture);
    if (!G_IS_UNIX_INPUT_STREAM(stream)) { close_capture(); return; }
    audio_fd=g_unix_input_stream_get_fd(G_UNIX_INPUT_STREAM(stream));
    int flags=fcntl(audio_fd,F_GETFL);
    if (flags<0 || fcntl(audio_fd,F_SETFL,flags|O_NONBLOCK)<0) close_capture();
}
static void analyze(void) {
    double complex samples[SAMPLES];
    double energy=0;
    for (int i=0;i<SAMPLES;i++) {
        int16_t raw=(int16_t)((unsigned)frame[2*i] | ((unsigned)frame[2*i+1]<<8));
        double normalized=raw/32768.0;
        energy+=normalized*normalized;
        samples[i]=normalized*window[i];
    }
    double rms=sqrt(energy/SAMPLES);
    target_brightness=db_level(rms);
    if (rms < 1e-5) {
        memset(target,0,sizeof target);
        return;
    }
    /* FFT bands cover frequency ranges, including tones between their centers. */
    for (unsigned i=1,j=0;i<SAMPLES;i++) {
        unsigned bit=SAMPLES>>1;
        for (;j&bit;bit>>=1) j^=bit;
        j^=bit;
        if (i<j) { double complex tmp=samples[i]; samples[i]=samples[j]; samples[j]=tmp; }
    }
    for (int length=2;length<=SAMPLES;length*=2) {
        double complex step=cexp(-2*G_PI*I/length);
        for (int start=0;start<SAMPLES;start+=length) {
            double complex weight=1;
            for (int k=0;k<length/2;k++) {
                double complex even=samples[start+k];
                double complex odd=samples[start+k+length/2]*weight;
                samples[start+k]=even+odd;
                samples[start+k+length/2]=even-odd;
                weight*=step;
            }
        }
    }
    for (int b=0;b<N;b++) {
        double sum=0;
        for (int k=bin_start[b];k<bin_end[b];k++) {
            double real=creal(samples[k]),imag=cimag(samples[k]);
            sum+=real*real+imag*imag;
        }
        /* One-sided band power, compensated for the Hann window energy.
         * Equal-amplitude tones get equal height regardless of band width.
         * A fixed dBFS scale preserves changes in captured digital level.
         */
        double band_rms=sqrt(2*sum/(SAMPLES*window_energy));
        target[b]=db_level(band_rms);
    }
}
static gboolean tick(gpointer unused) {
    (void)unused;
    if (audio_fd<0) open_capture();
    /* Drain a bounded amount so a backed-up capture cannot stall the GTK loop. */
    for (int frames=0;audio_fd>=0 && frames<8;) {
        ssize_t n=read(audio_fd,frame+have,sizeof frame-have);
        if (n>0) {
            have+=(size_t)n;
            if (have==sizeof frame) {
                analyze();
                memmove(frame,frame+HOP*2,sizeof frame-HOP*2);
                have=sizeof frame-HOP*2;
                frames++;
            }
        } else if (n==0 || (errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR)) {
            close_capture(); memset(target,0,sizeof target); target_brightness=0; break;
        } else if (errno==EINTR) continue;
        else break;
    }
    gboolean changed=FALSE;
    double previous_brightness=brightness;
    brightness+=(target_brightness-brightness)*(target_brightness>brightness?.65:.20);
    if (brightness<.003) brightness=0;
    changed |= fabs(brightness-previous_brightness)>.001;
    for (int i=0;i<N;i++) {
        double old=levels[i];
        levels[i]+=(target[i]-levels[i])*(target[i]>levels[i]?.68:.24);
        if (levels[i]<.003) levels[i]=0;
        changed |= fabs(levels[i]-old)>.001;
    }
    if (changed) for (GList *p=instances;p;p=p->next)
        gtk_widget_queue_draw(((Instance*)p->data)->area);
    return G_SOURCE_CONTINUE;
}
static gboolean draw(GtkWidget *widget,cairo_t *cr,gpointer data) {
    Instance *inst=data;
    paint(cr,gtk_widget_get_allocated_width(widget),
             gtk_widget_get_allocated_height(widget),levels,inst->embedded,brightness);
    return FALSE;
}
void *wbcffi_init(const Init *info,const Entry *entries,size_t count) {
    Instance *inst=g_new0(Instance,1);
    for (size_t i=0;i<count;i++) {
        if (strcmp(entries[i].key,"embedded")==0) {
            char *value=g_strdup(entries[i].value);
            inst->embedded=strcmp(g_strstrip(value),"true")==0;
            g_free(value);
        }
    }
    inst->area=gtk_drawing_area_new();
    /* Keep a reference until deinit regardless of container teardown order. */
    g_object_ref_sink(inst->area);
    gtk_widget_set_name(inst->area,"audio-pill-native");
    gtk_widget_set_size_request(inst->area,PILL_WIDTH,inst->embedded?18:28);
    gtk_widget_set_margin_start(inst->area,inst->embedded?0:5);
    gtk_widget_set_margin_top(inst->area,inst->embedded?0:3);
    gtk_widget_set_margin_bottom(inst->area,inst->embedded?0:3);
    inst->draw_handler=g_signal_connect(inst->area,"draw",G_CALLBACK(draw),inst);
    gtk_container_add(info->get_root_widget(info->obj),inst->area);
    gtk_widget_show(inst->area);
    instances=g_list_prepend(instances,inst);
    if (!timer) {
        prepare_analysis();
        timer=g_timeout_add(50,tick,NULL);
    }
    return inst;
}
void wbcffi_deinit(void *ptr) {
    Instance *inst=ptr;
    instances=g_list_remove(instances,inst);
    g_signal_handler_disconnect(inst->area,inst->draw_handler);
    g_object_unref(inst->area);
    g_free(inst);
    if (!instances) {
        if (timer) g_source_remove(timer);
        timer=0; close_capture();
        memset(levels,0,sizeof levels); memset(target,0,sizeof target);
        brightness=target_brightness=0; retry_at=0;
    }
}
void wbcffi_update(void *ptr) { (void)ptr; }
#endif
