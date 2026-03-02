import { shortest } from "@antiwork/shortest";

// Dashboard / Home page
shortest("Log in with username 'admin' and password 'shadow', then verify the dashboard shows the router hero section with Internet status, Wi-Fi SSID, connected device count, and uptime");

shortest("On the dashboard, verify the Details section shows real data for Public IP, Local IP, Uptime, CPU percentage, Memory percentage, and Connections count — none should show '...' or be empty");

shortest("On the dashboard, verify the CPU History and Memory History charts are rendered with canvas elements");

shortest("On the dashboard, verify the Latency section shows ping times for Google DNS, Cloudflare, and Router");

shortest("On the dashboard, verify the Disk Usage section shows at least one mount point with size and usage percentage");

shortest("Click the 'Refresh' button on the dashboard and verify the data reloads without errors");
