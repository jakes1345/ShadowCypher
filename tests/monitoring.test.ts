import { shortest } from "@antiwork/shortest";

// Monitoring
shortest("Log in with 'admin'/'shadow', click 'Monitoring' in the sidebar, and verify the page shows Bandwidth (Live) with network interface names and download/upload rates");

shortest("On the Monitoring page, verify the Processes table shows at least 10 processes with PID, User, CPU%, MEM%, and Command columns");

shortest("On the Monitoring page, verify the USB Devices section is visible");
