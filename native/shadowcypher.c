/*
 * ShadowCypher — GTK 3 desktop for Linux (native UI, no embedded browser).
 * Build: make   Run: ./shadowcypher
 */

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

#include <gtk/gtk.h>

#define APP_TITLE "ShadowCypher"
#define APP_ID "shadow.shadowcypher"
#define OUT_MAX (512 * 1024)
#define USER_LINE_MAX 1024
#define USER_ARG_MAX 48
#define USER_ARG_LEN 512

enum { PAGE_OVERVIEW, PAGE_NETWORK, PAGE_SYSTEM, PAGE_FIREWALL, PAGE_LOGS, PAGE_TOOLS, N_PAGES };

static const char *PAGE_IDS[] = {
    "overview", "network", "system", "firewall", "logs", "tools"
};

static const char *PAGE_LABELS[] = {
    "Overview", "Network", "System", "Firewall", "Logs", "Tools"
};

static char project_root[4096];

static const char *find_project_root(void)
{
    char cwd[4096], exe[4096];

    if (getcwd(cwd, sizeof cwd)) {
        char try_path[4096];
        snprintf(try_path, sizeof try_path, "%s/native/shadowcypher.c", cwd);
        if (access(try_path, F_OK) == 0) {
            snprintf(project_root, sizeof project_root, "%s", cwd);
            return project_root;
        }
    }

    ssize_t len = readlink("/proc/self/exe", exe, sizeof exe - 1);
    if (len > 0) {
        exe[len] = '\0';
        char *slash = strrchr(exe, '/');
        if (slash) {
            *slash = '\0';
            char try_path[4096];
            snprintf(try_path, sizeof try_path, "%s/../native/shadowcypher.c", exe);
            if (access(try_path, F_OK) == 0) {
                snprintf(project_root, sizeof project_root, "%s/..", exe);
                return project_root;
            }
            snprintf(try_path, sizeof try_path, "%s/native/shadowcypher.c", exe);
            if (access(try_path, F_OK) == 0) {
                snprintf(project_root, sizeof project_root, "%s", exe);
                return project_root;
            }
        }
    }

    if (getcwd(cwd, sizeof cwd))
        snprintf(project_root, sizeof project_root, "%s", cwd);
    else
        snprintf(project_root, sizeof project_root, ".");
    return project_root;
}

static unsigned long long g_prev_idle, g_prev_total;

static int read_cpu_times(unsigned long long *idle_out, unsigned long long *total_out)
{
    FILE *f = fopen("/proc/stat", "r");
    if (!f) return 0;
    char line[256];
    if (!fgets(line, sizeof line, f)) {
        fclose(f);
        return 0;
    }
    fclose(f);
    unsigned long long u, n, s, id, io, irq, sirq, steal, guest, gnice;
    int nscan = sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
                       &u, &n, &s, &id, &io, &irq, &sirq, &steal, &guest, &gnice);
    if (nscan < 4) return 0;
    *idle_out = id;
    *total_out = u + n + s + id + io + irq + sirq + steal + guest + gnice;
    return 1;
}

static double cpu_percent_sample(void)
{
    unsigned long long idle, total;
    if (!read_cpu_times(&idle, &total)) return 0.0;
    unsigned long long di = idle - g_prev_idle;
    unsigned long long dt = total - g_prev_total;
    g_prev_idle = idle;
    g_prev_total = total;
    if (dt == 0) return 0.0;
    return (1.0 - (double)di / (double)dt) * 100.0;
}

static void mem_percent(double *used_pct, char *buf, size_t buflen)
{
    FILE *f = fopen("/proc/meminfo", "r");
    if (!f) {
        *used_pct = 0;
        snprintf(buf, buflen, "N/A");
        return;
    }
    unsigned long mt = 0, ma = 0;
    char line[256];
    while (fgets(line, sizeof line, f)) {
        if (strncmp(line, "MemTotal:", 9) == 0)
            sscanf(line + 9, "%lu", &mt);
        else if (strncmp(line, "MemAvailable:", 13) == 0)
            sscanf(line + 13, "%lu", &ma);
    }
    fclose(f);
    if (mt == 0) {
        *used_pct = 0;
        snprintf(buf, buflen, "N/A");
        return;
    }
    *used_pct = 100.0 * (double)(mt - ma) / (double)mt;
    snprintf(buf, buflen, "%.1f%% (avail %.1f GB)", *used_pct, ma / 1048576.0);
}

typedef struct {
    GtkTextBuffer *buffer;
    char *text;
    GtkWidget *sensitive_widget;
} IdleSetText;

static gboolean idle_set_buffer_text(gpointer data)
{
    IdleSetText *d = data;
    if (d->buffer && d->text)
        gtk_text_buffer_set_text(d->buffer, d->text, -1);
    if (d->sensitive_widget)
        gtk_widget_set_sensitive(d->sensitive_widget, TRUE);
    g_free(d->text);
    g_free(d);
    return G_SOURCE_REMOVE;
}

typedef struct {
    char *cmd;
    GtkTextBuffer *buffer;
} CmdJob;

static void capped_read(FILE *p, GString *out)
{
    char line[4096];
    while (fgets(line, sizeof line, p) && out->len < OUT_MAX)
        g_string_append(out, line);
    if (out->len >= OUT_MAX)
        g_string_append(out, "\n[output truncated]\n");
}

static gpointer thread_run_cmd(gpointer data)
{
    CmdJob *job = data;
    GString *out = g_string_new(NULL);

    FILE *p = popen(job->cmd, "r");
    if (p) {
        capped_read(p, out);
        pclose(p);
    } else {
        g_string_append_printf(out, "popen failed: %s\n", strerror(errno));
    }

    IdleSetText *idle = g_new0(IdleSetText, 1);
    idle->buffer = job->buffer;
    idle->text = g_string_free(out, FALSE);
    g_idle_add(idle_set_buffer_text, idle);
    g_free(job->cmd);
    g_free(job);
    return NULL;
}

static void run_cmd_async(GtkTextBuffer *buf, const char *cmd)
{
    CmdJob *job = g_new0(CmdJob, 1);
    job->cmd = g_strdup(cmd);
    job->buffer = buf;
    g_thread_new("sc_cmd", thread_run_cmd, job);
}

static int user_arg_char_ok(char c)
{
    if (isalnum((unsigned char)c)) return 1;
    return c == '.' || c == '_' || c == '-' || c == '/' || c == '@' || c == ':' || c == '=' || c == '+' || c == '%';
}

static void free_argv_local(char **argv, int n)
{
    for (int i = 0; i < n; i++) {
        g_free(argv[i]);
        argv[i] = NULL;
    }
}

static int user_parse_and_check(const char *line, char **argv, int *argc_out)
{
    char buf[USER_LINE_MAX];
    size_t n = strlen(line);
    if (n == 0 || n >= sizeof buf) return -1;
    memcpy(buf, line, n + 1);

    int argc = 0;
    char *p = buf;
    while (*p && argc < USER_ARG_MAX) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        char *start = p;
        while (*p && *p != ' ' && *p != '\t') p++;
        if (*p) *p++ = '\0';
        size_t alen = strlen(start);
        if (alen == 0 || alen >= USER_ARG_LEN) {
            free_argv_local(argv, argc);
            return -1;
        }
        for (size_t i = 0; i < alen; i++) {
            if (!user_arg_char_ok((unsigned char)start[i])) {
                free_argv_local(argv, argc);
                return -1;
            }
        }
        argv[argc++] = g_strdup(start);
    }
    if (argc == 0) {
        free_argv_local(argv, argc);
        return -1;
    }
    *argc_out = argc;
    return 0;
}

typedef struct {
    char **argv;
    int argc;
    GtkTextBuffer *buffer;
    GtkWidget *run_btn;
} UserCmdJob;

static gpointer thread_run_user_cmd(gpointer data)
{
    UserCmdJob *job = data;
    GString *out = g_string_new(NULL);

    int pipefd[2];
    if (pipe(pipefd) < 0) {
        g_string_append_printf(out, "pipe: %s\n", strerror(errno));
        goto done;
    }

    pid_t pid = fork();
    if (pid < 0) {
        g_string_append_printf(out, "fork: %s\n", strerror(errno));
        close(pipefd[0]);
        close(pipefd[1]);
        goto done;
    }

    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);
        close(STDIN_FILENO);
        signal(SIGPIPE, SIG_DFL);
        execvp(job->argv[0], job->argv);
        _exit(127);
    }

    close(pipefd[1]);
    FILE *fp = fdopen(pipefd[0], "r");
    if (fp) {
        capped_read(fp, out);
        fclose(fp);
    } else {
        close(pipefd[0]);
    }

    int st;
    waitpid(pid, &st, 0);
    if (WIFEXITED(st) && WEXITSTATUS(st) == 127)
        g_string_append(out, "[command not found or not executable]\n");

done:
    for (int i = 0; i < job->argc; i++)
        g_free(job->argv[i]);
    g_free(job->argv);

    IdleSetText *idle = g_new0(IdleSetText, 1);
    idle->buffer = job->buffer;
    idle->text = g_string_free(out, FALSE);
    idle->sensitive_widget = job->run_btn;
    g_idle_add(idle_set_buffer_text, idle);
    g_free(job);
    return NULL;
}

static void run_user_cmd(GtkTextBuffer *buf, GtkWidget *run_btn, const char *line)
{
    char *argv[USER_ARG_MAX];
    int argc = 0;
    if (user_parse_and_check(line, argv, &argc) != 0) {
        gtk_text_buffer_set_text(buf,
            "Invalid input. Use space-separated arguments only; "
            "allowed characters per token: letters, digits, ._-/@:=+%\n"
            "Example: ping -c 4 8.8.8.8\n", -1);
        return;
    }

    gtk_widget_set_sensitive(run_btn, FALSE);

    UserCmdJob *job = g_new0(UserCmdJob, 1);
    job->argv = g_new0(char *, (gsize)argc + 1);
    for (int i = 0; i < argc; i++)
        job->argv[i] = argv[i];
    job->argv[argc] = NULL;
    job->argc = argc;
    job->buffer = buf;
    job->run_btn = run_btn;
    g_thread_new("sc_user", thread_run_user_cmd, job);
}

typedef struct {
    GtkWidget *l_host, *l_up, *l_kern, *l_cpu, *l_mem, *l_load, *l_disk, *l_ip;
    guint tick;
} OverviewCtx;

static gboolean overview_tick(gpointer data)
{
    OverviewCtx *o = data;
    char b[512];
    FILE *f;

    f = fopen("/proc/loadavg", "r");
    if (f) {
        if (fgets(b, sizeof b, f))
            gtk_label_set_text(GTK_LABEL(o->l_load), b);
        fclose(f);
    }

    double cpu = cpu_percent_sample();
    snprintf(b, sizeof b, "%.1f%%", cpu);
    gtk_label_set_text(GTK_LABEL(o->l_cpu), b);

    double mp;
    mem_percent(&mp, b, sizeof b);
    gtk_label_set_text(GTK_LABEL(o->l_mem), b);

    f = popen("df -h / 2>/dev/null | tail -1", "r");
    if (f) {
        if (fgets(b, sizeof b, f)) {
            b[strcspn(b, "\n")] = 0;
            gtk_label_set_text(GTK_LABEL(o->l_disk), b);
        }
        pclose(f);
    }

    f = popen("hostname", "r");
    if (f) {
        if (fgets(b, sizeof b, f)) {
            b[strcspn(b, "\n")] = 0;
            gtk_label_set_text(GTK_LABEL(o->l_host), b);
        }
        pclose(f);
    }

    f = popen("uptime -p 2>/dev/null || uptime", "r");
    if (f) {
        if (fgets(b, sizeof b, f)) {
            b[strcspn(b, "\n")] = 0;
            gtk_label_set_text(GTK_LABEL(o->l_up), b);
        }
        pclose(f);
    }

    f = popen("uname -r", "r");
    if (f) {
        if (fgets(b, sizeof b, f)) {
            b[strcspn(b, "\n")] = 0;
            gtk_label_set_text(GTK_LABEL(o->l_kern), b);
        }
        pclose(f);
    }

    f = popen("curl -4sS --max-time 4 https://ifconfig.me/ip 2>/dev/null || echo N/A", "r");
    if (f) {
        if (fgets(b, sizeof b, f)) {
            b[strcspn(b, "\n")] = 0;
            gtk_label_set_text(GTK_LABEL(o->l_ip), b);
        }
        pclose(f);
    }

    return G_SOURCE_CONTINUE;
}

static GtkWidget *make_label_row(const char *title, GtkWidget **val_out)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    GtkWidget *t = gtk_label_new(title);
    gtk_widget_set_halign(t, GTK_ALIGN_START);
    gtk_label_set_xalign(GTK_LABEL(t), 0);
    gtk_box_pack_start(GTK_BOX(box), t, FALSE, FALSE, 0);
    GtkWidget *v = gtk_label_new("-");
    gtk_label_set_xalign(GTK_LABEL(v), 0);
    gtk_label_set_selectable(GTK_LABEL(v), TRUE);
    gtk_box_pack_start(GTK_BOX(box), v, TRUE, TRUE, 0);
    *val_out = v;
    return box;
}

static GtkWidget *build_overview_page(OverviewCtx *ctx)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_margin_start(box, 16);
    gtk_widget_set_margin_end(box, 16);
    gtk_widget_set_margin_top(box, 16);
    gtk_widget_set_margin_bottom(box, 16);

    GtkWidget *title = gtk_label_new("System overview");
    gtk_style_context_add_class(gtk_widget_get_style_context(title), "title-1");
    gtk_label_set_xalign(GTK_LABEL(title), 0);
    gtk_box_pack_start(GTK_BOX(box), title, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(box), make_label_row("Hostname", &ctx->l_host), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("Uptime", &ctx->l_up), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("Kernel", &ctx->l_kern), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("Load", &ctx->l_load), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("CPU", &ctx->l_cpu), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("Memory", &ctx->l_mem), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("Disk /", &ctx->l_disk), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(box), make_label_row("Public IP", &ctx->l_ip), FALSE, FALSE, 0);

    /* Prime the CPU sample: first read sets baseline, second computes delta. */
    read_cpu_times(&g_prev_idle, &g_prev_total);
    overview_tick(ctx);

    ctx->tick = g_timeout_add(2000, overview_tick, ctx);
    return box;
}

static void overview_win_destroy(GtkWidget *w, gpointer data)
{
    (void)w;
    OverviewCtx *ctx = data;
    if (ctx && ctx->tick)
        g_source_remove(ctx->tick);
    g_free(ctx);
}

static GtkWidget *page_scrolled_text(GtkTextBuffer **buf_out)
{
    GtkWidget *sw = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(sw),
        GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    GtkWidget *tv = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(tv), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(tv), TRUE);
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(tv), GTK_WRAP_WORD_CHAR);
    GtkTextBuffer *buf = gtk_text_view_get_buffer(GTK_TEXT_VIEW(tv));
    *buf_out = buf;
    gtk_container_add(GTK_CONTAINER(sw), tv);
    return sw;
}

static void on_row_selected(GtkListBox *lb, GtkListBoxRow *row, gpointer user_data)
{
    GtkWidget *stack = GTK_WIDGET(user_data);
    (void)lb;
    if (!row)
        return;
    int i = gtk_list_box_row_get_index(row);
    if (i >= 0 && i < N_PAGES)
        gtk_stack_set_visible_child_name(GTK_STACK(stack), PAGE_IDS[i]);
}

static void on_stack_visible_child(GObject *stack_obj, GParamSpec *ps, gpointer data)
{
    (void)ps;
    GtkStack *stack = GTK_STACK(stack_obj);
    GtkTextBuffer **bufs = data;
    const char *name = gtk_stack_get_visible_child_name(stack);
    if (!name) return;

    if (strcmp(name, "network") == 0)
        run_cmd_async(bufs[0],
            "/sbin/ip -br addr 2>/dev/null; echo; /sbin/ip route 2>/dev/null; echo; "
            "ss -tlnp 2>/dev/null | head -80");
    else if (strcmp(name, "system") == 0)
        run_cmd_async(bufs[1],
            "uname -a 2>/dev/null; echo; lscpu 2>/dev/null | head -40; echo; "
            "cat /proc/meminfo | head -8");
    else if (strcmp(name, "firewall") == 0)
        run_cmd_async(bufs[2],
            "(command -v nft >/dev/null && nft list ruleset 2>&1) || "
            "(command -v iptables >/dev/null && iptables -L -n -v 2>&1) || "
            "echo 'No nft or iptables found.'");
    else if (strcmp(name, "logs") == 0)
        run_cmd_async(bufs[3],
            "(command -v journalctl >/dev/null && journalctl -n 120 --no-pager 2>&1) || "
            "tail -n 120 /var/log/syslog 2>&1 || echo 'No journalctl/syslog.'");
}

typedef struct {
    GtkWidget *entry;
    GtkWidget *run;
    GtkTextBuffer *out;
} ToolsCtx;

static void tools_run_clicked(GtkButton *btn, gpointer data)
{
    (void)btn;
    ToolsCtx *t = data;
    const char *user = gtk_entry_get_text(GTK_ENTRY(t->entry));
    if (!user || !*user) return;
    run_user_cmd(t->out, t->run, user);
}

static GtkWidget *build_tools_page(ToolsCtx *ctx)
{
    GtkWidget *v = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_start(v, 16);
    gtk_widget_set_margin_end(v, 16);
    gtk_widget_set_margin_top(v, 16);
    gtk_widget_set_margin_bottom(v, 16);

    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    ctx->entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(ctx->entry),
        "program arg arg ... (no shell; see help text below)");
    gtk_widget_set_hexpand(ctx->entry, TRUE);
    ctx->run = gtk_button_new_with_label("Run");
    g_signal_connect(ctx->run, "clicked", G_CALLBACK(tools_run_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(row), ctx->entry, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(row), ctx->run, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(v), row, FALSE, FALSE, 0);

    GtkWidget *hint = gtk_label_new(
        "Runs the program with execvp (no shell). Tokens: letters, digits, ._-/@:=+% only. "
        "Max " G_STRINGIFY(USER_ARG_MAX) " args.");
    gtk_label_set_line_wrap(GTK_LABEL(hint), TRUE);
    gtk_label_set_xalign(GTK_LABEL(hint), 0);
    gtk_style_context_add_class(gtk_widget_get_style_context(hint), "dim-label");
    gtk_box_pack_start(GTK_BOX(v), hint, FALSE, FALSE, 0);

    GtkTextBuffer *buf;
    GtkWidget *sw = page_scrolled_text(&buf);
    ctx->out = buf;
    gtk_widget_set_vexpand(sw, TRUE);
    gtk_box_pack_start(GTK_BOX(v), sw, TRUE, TRUE, 0);
    return v;
}

static void tools_win_destroy(GtkWidget *w, gpointer data)
{
    (void)w;
    g_free(data);
}

static void bufs_destroy_free(GtkWidget *w, gpointer data)
{
    (void)w;
    g_free(data);
}

static void apply_css(GtkWidget *w)
{
    GtkCssProvider *css = gtk_css_provider_new();
    const char *data =
        "@define-color bg #0f1114;"
        "@define-color fg #d8dce4;"
        "window { background-color: @bg; color: @fg; }"
        "list { background-color: #141820; color: @fg; }"
        "list row:selected { background-color: #1e2a32; color: #7cb8ff; }"
        "textview { background-color: #0a0c10; color: #d0d4dc; }"
        ".title-1 { font-size: 17px; font-weight: 600; color: #a8c8e8; }"
        ".dim-label { font-size: 11px; color: #6a7280; }";
    gtk_css_provider_load_from_data(css, data, -1, NULL);
    gtk_style_context_add_provider_for_screen(gdk_screen_get_default(),
        GTK_STYLE_PROVIDER(css), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(css);
    gtk_widget_set_name(w, "main-window");
}

static void on_activate(GtkApplication *app, gpointer user_data)
{
    (void)user_data;

    GtkWidget *win = gtk_application_window_new(app);
    gtk_window_set_title(GTK_WINDOW(win), APP_TITLE);
    gtk_window_set_default_size(GTK_WINDOW(win), 1100, 720);
    gtk_window_set_position(GTK_WINDOW(win), GTK_WIN_POS_CENTER);

    apply_css(win);

    find_project_root();
    if (chdir(project_root) != 0)
        g_warning("chdir(%s): %s", project_root, g_strerror(errno));

    GtkWidget *hb = gtk_header_bar_new();
    gtk_header_bar_set_title(GTK_HEADER_BAR(hb), APP_TITLE);
    gtk_header_bar_set_show_close_button(GTK_HEADER_BAR(hb), TRUE);
    gtk_window_set_titlebar(GTK_WINDOW(win), hb);

    GtkWidget *paned = gtk_paned_new(GTK_ORIENTATION_HORIZONTAL);
    gtk_container_add(GTK_CONTAINER(win), paned);

    GtkWidget *list = gtk_list_box_new();
    gtk_widget_set_size_request(list, 180, -1);
    gtk_style_context_add_class(gtk_widget_get_style_context(list), "sidebar");
    for (int i = 0; i < N_PAGES; i++) {
        GtkWidget *row = gtk_label_new(PAGE_LABELS[i]);
        gtk_widget_set_margin_start(row, 12);
        gtk_widget_set_margin_end(row, 12);
        gtk_widget_set_margin_top(row, 8);
        gtk_widget_set_margin_bottom(row, 8);
        gtk_label_set_xalign(GTK_LABEL(row), 0);
        gtk_container_add(GTK_CONTAINER(list), row);
    }

    GtkWidget *stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_SLIDE_LEFT_RIGHT);
    gtk_stack_set_transition_duration(GTK_STACK(stack), 200);

    OverviewCtx *ov = g_new0(OverviewCtx, 1);
    GtkWidget *w_over = build_overview_page(ov);
    gtk_stack_add_named(GTK_STACK(stack), w_over, PAGE_IDS[PAGE_OVERVIEW]);

    GtkTextBuffer *b_net, *b_sys, *b_fw, *b_log;
    gtk_stack_add_named(GTK_STACK(stack), page_scrolled_text(&b_net), PAGE_IDS[PAGE_NETWORK]);
    gtk_stack_add_named(GTK_STACK(stack), page_scrolled_text(&b_sys), PAGE_IDS[PAGE_SYSTEM]);
    gtk_stack_add_named(GTK_STACK(stack), page_scrolled_text(&b_fw), PAGE_IDS[PAGE_FIREWALL]);
    gtk_stack_add_named(GTK_STACK(stack), page_scrolled_text(&b_log), PAGE_IDS[PAGE_LOGS]);

    ToolsCtx *tools = g_new0(ToolsCtx, 1);
    gtk_stack_add_named(GTK_STACK(stack), build_tools_page(tools), PAGE_IDS[PAGE_TOOLS]);

    GtkTextBuffer **bufs = g_new0(GtkTextBuffer *, 4);
    bufs[0] = b_net;
    bufs[1] = b_sys;
    bufs[2] = b_fw;
    bufs[3] = b_log;
    g_signal_connect(stack, "notify::visible-child", G_CALLBACK(on_stack_visible_child), bufs);

    gtk_paned_pack1(GTK_PANED(paned), list, FALSE, FALSE);
    gtk_paned_pack2(GTK_PANED(paned), stack, TRUE, FALSE);
    gtk_paned_set_position(GTK_PANED(paned), 200);

    g_signal_connect(list, "row-selected", G_CALLBACK(on_row_selected), stack);

    gtk_list_box_select_row(GTK_LIST_BOX(list), gtk_list_box_get_row_at_index(GTK_LIST_BOX(list), 0));

    g_signal_connect(win, "destroy", G_CALLBACK(overview_win_destroy), ov);
    g_signal_connect(win, "destroy", G_CALLBACK(tools_win_destroy), tools);
    g_signal_connect(win, "destroy", G_CALLBACK(bufs_destroy_free), bufs);

    gtk_widget_show_all(win);
}

int main(int argc, char **argv)
{
#if GLIB_CHECK_VERSION(2, 74, 0)
    GApplicationFlags flags = G_APPLICATION_DEFAULT_FLAGS;
#else
    GApplicationFlags flags = G_APPLICATION_FLAGS_NONE;
#endif
    GtkApplication *app = gtk_application_new(APP_ID, flags);
    g_signal_connect(app, "activate", G_CALLBACK(on_activate), NULL);
    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
