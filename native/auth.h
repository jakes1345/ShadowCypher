/*
 * Authentication header for ShadowCypher desktop app
 */

#ifndef SHADOWCYPHER_AUTH_H
#define SHADOWCYPHER_AUTH_H

int auth_init(void);
void auth_logout(void);
int auth_is_authenticated(void);
char *auth_get_token(void);
int auth_login(const char *email, const char *password);
int auth_save_token(void);

#endif
