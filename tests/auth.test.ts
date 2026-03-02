import { shortest } from "@antiwork/shortest";

// Authentication
shortest("Navigate to the app and verify the login modal appears with username and password fields and an ACCESS button");

shortest("Try logging in with wrong credentials 'admin' and 'wrongpass' and verify an error message appears");

shortest("Log in with username 'admin' and password 'shadow' and verify the login modal disappears and the dashboard loads");

shortest("After logging in, verify the sidebar shows 'Router' branding and a green 'Online' status dot at the bottom");
