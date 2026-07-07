/*
 * Authentication module for ShadowCypher desktop app
 * Handles JWT token management and API authentication
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <curl/curl.h>

#define AUTH_TOKEN_FILE ".local/share/shadowcypher/auth_token"
#define AUTH_API "http://api.shadowcypher.site/v1/auth"

typedef struct {
    char *token;
    char *user_id;
    char *username;
} AuthContext;

static AuthContext g_auth = {0};

// Memory callback for curl responses
typedef struct {
    char *data;
    size_t size;
} CurlResponse;

static size_t auth_curl_write_callback(void *contents, size_t size, size_t nmemb, void *userp)
{
    size_t realsize = size * nmemb;
    CurlResponse *resp = (CurlResponse *)userp;

    char *ptr = realloc(resp->data, resp->size + realsize + 1);
    if (!ptr) return 0;

    resp->data = ptr;
    memcpy(&(resp->data[resp->size]), contents, realsize);
    resp->size += realsize;
    resp->data[resp->size] = 0;

    return realsize;
}

int auth_login(const char *email, const char *password)
{
    CURL *curl = curl_easy_init();
    if (!curl) return 0;

    // Build JSON request with escaped quotes
    char json[1024];
    snprintf(json, sizeof json, "{\"email\":\"%s\",\"password\":\"%s\"}", email, password);

    CurlResponse response = {0};
    response.data = malloc(1);

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, AUTH_API "/login");
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, auth_curl_write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void *)&response);

    CURLcode res = curl_easy_perform(curl);

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        free(response.data);
        return 0;
    }

    // Parse JSON response (simplified - in production use a JSON library)
    // Look for "access_token" field
    char *token_start = strstr(response.data, "\"access_token\":\"");
    if (!token_start) {
        free(response.data);
        return 0;
    }

    token_start += 16;  // Skip past "\"access_token\":\""
    char *token_end = strchr(token_start, '"');
    if (!token_end) {
        free(response.data);
        return 0;
    }

    int token_len = token_end - token_start;
    g_auth.token = malloc(token_len + 1);
    strncpy(g_auth.token, token_start, token_len);
    g_auth.token[token_len] = 0;

    free(response.data);
    return 1;
}

int auth_save_token(const AuthContext *auth)
{
    char home[256];
    const char *h = getenv("HOME");
    if (!h) return 0;

    // Create directory if needed
    snprintf(home, sizeof home, "%s/.local/share/shadowcypher", h);
    mkdir(home, 0700);

    // Save token
    snprintf(home, sizeof home, "%s/.local/share/shadowcypher/auth_token", h);
    FILE *f = fopen(home, "w");
    if (!f) return 0;

    fprintf(f, "%s\n", auth->token);
    fclose(f);
    return 1;
}

int auth_load_token(AuthContext *auth)
{
    char home[256];
    const char *h = getenv("HOME");
    if (!h) return 0;

    snprintf(home, sizeof home, "%s/.local/share/shadowcypher/auth_token", h);
    FILE *f = fopen(home, "r");
    if (!f) return 0;

    char token[2048];
    if (!fgets(token, sizeof token, f)) {
        fclose(f);
        return 0;
    }
    fclose(f);

    // Remove newline
    token[strcspn(token, "\n")] = 0;
    auth->token = strdup(token);
    return 1;
}

void auth_clear_token(AuthContext *auth)
{
    if (auth->token) {
        free(auth->token);
        auth->token = NULL;
    }
    if (auth->user_id) {
        free(auth->user_id);
        auth->user_id = NULL;
    }
    if (auth->username) {
        free(auth->username);
        auth->username = NULL;
    }
}

int auth_is_authenticated(void)
{
    return g_auth.token != NULL;
}

char *auth_get_token(void)
{
    return g_auth.token;
}

int auth_init(void)
{
    // Try to load saved token
    if (auth_load_token(&g_auth)) {
        return 1;
    }
    return 0;
}

void auth_logout(void)
{
    auth_clear_token(&g_auth);
    // Remove token file
    char home[256];
    const char *h = getenv("HOME");
    if (h) {
        snprintf(home, sizeof home, "%s/.local/share/shadowcypher/auth_token", h);
        unlink(home);
    }
}
