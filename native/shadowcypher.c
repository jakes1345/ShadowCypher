/*
 * ShadowCypher - Native GTK3 + WebKitGTK Desktop App
 * Linux Mint Cinnamon native application
 *
 * Launches the Node.js server and embeds it in a native GTK window
 * using WebKitGTK. No Electron. Pure C + GTK.
 *
 * Build: make
 * Run:   ./shadowcypher
 */

#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <signal.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>

#define APP_TITLE       "ShadowCypher"
#define APP_URL         "http://127.0.0.1:3000"
#define SERVER_SCRIPT   "server.js"
#define HEALTH_RETRIES  40
#define HEALTH_DELAY_US 250000

static pid_t server_pid = -1;
static GtkWidget *window = NULL;
static GtkWidget *webview = NULL;
static GtkWidget *splash_label = NULL;
static GtkWidget *stack = NULL;

static char *find_project_root(void)
{
    static char root[4096];
    char exe[4096];
    ssize_t len = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
    if (len > 0) {
        exe[len] = '\0';
        char *dir = strrchr(exe, '/');
        if (dir) {
            *dir = '\0';
            char try_path[4096];
            snprintf(try_path, sizeof(try_path), "%s/../server.js", exe);
            if (access(try_path, F_OK) == 0) {
                snprintf(root, sizeof(root), "%s/..", exe);
                return root;
            }
            snprintf(try_path, sizeof(try_path), "%s/server.js", exe);
            if (access(try_path, F_OK) == 0) {
                snprintf(root, sizeof(root), "%s", exe);
                return root;
            }
        }
    }
    snprintf(root, sizeof(root), "/home/jack/ShadowCypher");
    return root;
}

static int server_is_running(void)
{
    char cmd[256];
    char buf[64];
    snprintf(cmd, sizeof(cmd),
        "curl -s -o /dev/null -w '%%{http_code}' --connect-timeout 1 %s/api/auth/status 2>/dev/null",
        APP_URL);
    FILE *fp = popen(cmd, "r");
    if (!fp) return 0;
    int ok = 0;
    if (fgets(buf, sizeof(buf), fp))
        ok = (strncmp(buf, "200", 3) == 0);
    pclose(fp);
    return ok;
}

static int start_server(void)
{
    char *root = find_project_root();
    char script[4096];

    if (server_is_running()) {
        fprintf(stderr, "[ShadowCypher] Server already running\n");
        return 1;
    }

    snprintf(script, sizeof(script), "%s/%s", root, SERVER_SCRIPT);
    if (access(script, F_OK) != 0) {
        fprintf(stderr, "[ShadowCypher] ERROR: %s not found\n", script);
        return 0;
    }

    server_pid = fork();
    if (server_pid < 0) { perror("fork"); return 0; }

    if (server_pid == 0) {
        if (chdir(root) != 0) { perror("chdir"); _exit(1); }
        char logpath[4096];
        snprintf(logpath, sizeof(logpath), "%s/native_server.log", root);
        FILE *lf = freopen(logpath, "a", stdout);
        if (lf) freopen(logpath, "a", stderr);
        execlp("node", "node", SERVER_SCRIPT, (char *)NULL);
        perror("execlp node");
        _exit(1);
    }

    fprintf(stderr, "[ShadowCypher] Server PID %d\n", server_pid);
    return 1;
}

static int wait_for_server(void)
{
    for (int i = 0; i < HEALTH_RETRIES; i++) {
        if (server_is_running()) return 1;
        usleep(HEALTH_DELAY_US);
    }
    return 0;
}

static void stop_server(void)
{
    if (server_pid > 0) {
        fprintf(stderr, "[ShadowCypher] Stopping server PID %d\n", server_pid);
        kill(server_pid, SIGTERM);
        int status;
        for (int i = 0; i < 20; i++) {
            if (waitpid(server_pid, &status, WNOHANG) != 0) break;
            usleep(100000);
        }
        if (waitpid(server_pid, &status, WNOHANG) == 0) {
            kill(server_pid, SIGKILL);
            waitpid(server_pid, &status, 0);
        }
        server_pid = -1;
    }
}

static gboolean on_delete_event(GtkWidget *w, GdkEvent *ev, gpointer d)
{
    (void)w; (void)ev; (void)d;
    stop_server();
    gtk_main_quit();
    return FALSE;
}

static void on_title_changed(WebKitWebView *wv, GParamSpec *ps, gpointer d)
{
    (void)ps; (void)d;
    const gchar *title = webkit_web_view_get_title(wv);
    if (title && strlen(title) > 0) {
        char buf[256];
        snprintf(buf, sizeof(buf), "%s — %s", APP_TITLE, title);
        gtk_window_set_title(GTK_WINDOW(window), buf);
    }
}

static gboolean server_ready_cb(gpointer d)
{
    (void)d;
    webkit_web_view_load_uri(WEBKIT_WEB_VIEW(webview), APP_URL);
    gtk_stack_set_visible_child_name(GTK_STACK(stack), "web");
    return G_SOURCE_REMOVE;
}

static gboolean server_failed_cb(gpointer d)
{
    (void)d;
    gtk_label_set_markup(GTK_LABEL(splash_label),
        "<span font='14' color='#ff4466'>Server failed to start.\n\n"
        "Check native_server.log</span>");
    return G_SOURCE_REMOVE;
}

static gpointer server_thread(gpointer d)
{
    (void)d;
    if (!start_server()) { g_idle_add(server_failed_cb, NULL); return NULL; }
    if (wait_for_server()) g_idle_add(server_ready_cb, NULL);
    else g_idle_add(server_failed_cb, NULL);
    return NULL;
}

static void apply_dark_css(GtkWidget *w)
{
    GtkCssProvider *css = gtk_css_provider_new();
    gtk_css_provider_load_from_data(css,
        "window { background-color: #020203; }"
        "label { color: #00d4ff; }", -1, NULL);
    gtk_style_context_add_provider(
        gtk_widget_get_style_context(w),
        GTK_STYLE_PROVIDER(css),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(css);
}

static void configure_webkit(WebKitWebView *wv)
{
    WebKitSettings *s = webkit_web_view_get_settings(wv);
    webkit_settings_set_enable_javascript(s, TRUE);
    webkit_settings_set_enable_developer_extras(s, TRUE);
    webkit_settings_set_javascript_can_access_clipboard(s, TRUE);
    webkit_settings_set_allow_modal_dialogs(s, TRUE);
    webkit_settings_set_enable_media(s, TRUE);
    webkit_settings_set_media_playback_requires_user_gesture(s, FALSE);

    WebKitWebContext *ctx = webkit_web_view_get_context(wv);
    WebKitCookieManager *ck = webkit_web_context_get_cookie_manager(ctx);
    webkit_cookie_manager_set_accept_policy(ck, WEBKIT_COOKIE_POLICY_ACCEPT_ALWAYS);
}

int main(int argc, char *argv[])
{
    gtk_init(&argc, &argv);

    g_object_set(gtk_settings_get_default(),
        "gtk-application-prefer-dark-theme", TRUE, NULL);

    window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), APP_TITLE);
    gtk_window_set_default_size(GTK_WINDOW(window), 1400, 900);
    gtk_window_set_position(GTK_WINDOW(window), GTK_WIN_POS_CENTER);
    g_signal_connect(window, "delete-event", G_CALLBACK(on_delete_event), NULL);

    /* Cyan tinted icon */
    GdkPixbuf *icon = gdk_pixbuf_new(GDK_COLORSPACE_RGB, TRUE, 8, 64, 64);
    gdk_pixbuf_fill(icon, 0x00d4ff80);
    gtk_window_set_icon(GTK_WINDOW(window), icon);
    g_object_unref(icon);

    stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    gtk_stack_set_transition_duration(GTK_STACK(stack), 400);
    gtk_container_add(GTK_CONTAINER(window), stack);

    /* Splash */
    GtkWidget *splash = gtk_box_new(GTK_ORIENTATION_VERTICAL, 20);
    gtk_widget_set_halign(splash, GTK_ALIGN_CENTER);
    gtk_widget_set_valign(splash, GTK_ALIGN_CENTER);
    apply_dark_css(splash);

    splash_label = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(splash_label),
        "<span font='24' color='#00d4ff' weight='bold'>SHADOWCYPHER</span>\n\n"
        "<span font='11' color='#4a4a5a'>Starting server...</span>");
    gtk_label_set_justify(GTK_LABEL(splash_label), GTK_JUSTIFY_CENTER);
    gtk_box_pack_start(GTK_BOX(splash), splash_label, FALSE, FALSE, 0);

    GtkWidget *spinner = gtk_spinner_new();
    gtk_spinner_start(GTK_SPINNER(spinner));
    gtk_box_pack_start(GTK_BOX(splash), spinner, FALSE, FALSE, 0);

    gtk_stack_add_named(GTK_STACK(stack), splash, "splash");

    /* WebView */
    webview = webkit_web_view_new();
    configure_webkit(WEBKIT_WEB_VIEW(webview));
    g_signal_connect(webview, "notify::title", G_CALLBACK(on_title_changed), NULL);

    GdkRGBA bg = { 0.008, 0.008, 0.012, 1.0 };
    webkit_web_view_set_background_color(WEBKIT_WEB_VIEW(webview), &bg);
    gtk_stack_add_named(GTK_STACK(stack), webview, "web");

    gtk_stack_set_visible_child_name(GTK_STACK(stack), "splash");
    apply_dark_css(window);
    gtk_widget_show_all(window);

    g_thread_new("server", server_thread, NULL);
    gtk_main();
    return 0;
}
