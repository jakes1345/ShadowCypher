import { shortest } from "@antiwork/shortest";

// Terminal
shortest("Log in with 'admin'/'shadow', click 'Terminal' in the sidebar, and verify a terminal appears with a '$' prompt input");

// File Browser
shortest("Click 'Files' in the sidebar and verify the file browser loads showing the path '/home/jack' with a list of files and directories including columns for Name, Size, Modified, and Permissions");

shortest("In the file browser, click 'Up' and verify the path changes to '/home'");

// System
shortest("Click 'System' in the sidebar and verify the page shows Host Info, GPU, Users table, Cron Jobs, PCI Devices, Startup Services, and Kernel Modules sections");

// Logs
shortest("Click 'Logs' in the sidebar and verify the page shows a log viewer with a dropdown for Syslog/Auth/Kernel/Journal/Minecraft and a line count selector");

// Packages
shortest("Click 'Packages' in the sidebar, type 'curl' in the search box and click Search, then verify results appear showing package names and descriptions");
