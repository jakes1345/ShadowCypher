import { shortest } from "@antiwork/shortest";

// System Diagnostic
shortest("Log in with 'admin'/'shadow', click 'Diagnostic' in the sidebar, and verify the page runs a diagnostic showing System Status and Installed Tools sections");

shortest("On the Diagnostic page, verify the Installed Tools section shows status for nmap, nikto, sqlmap, proxychains, tshark, and tcpdump — each marked as either installed (green checkmark) or not found");
