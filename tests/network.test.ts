import { shortest } from "@antiwork/shortest";

// Wi-Fi page
shortest("Log in with 'admin'/'shadow', click 'Wi-Fi' in the sidebar, and verify the Wi-Fi page shows the current SSID connection info and a Nearby Networks table");

shortest("On the Wi-Fi page, verify the Interfaces table shows at least one network interface with its state (UP or DOWN)");

shortest("On the Wi-Fi page, verify the DNS section shows at least one nameserver IP address");

// Connected Devices
shortest("Click 'Connected Devices' in the sidebar and verify a table appears showing devices with IP, MAC, Hostname, and Status columns");

shortest("On the Connected Devices page, verify at least one device is listed with an IP address in the 192.168.x.x or 172.x.x.x range");

shortest("Click the 'Rescan' button on the Connected Devices page and verify the page refreshes without errors");

// Port Forwarding
shortest("Click 'Port Forwarding' in the sidebar and verify the page shows an 'Add rule' form with External port, Internal IP, Internal port, and Protocol fields");

// Firewall
shortest("Click 'Firewall' in the sidebar and verify the page shows iptables Rules section, an IP block/unblock input, a port open/close input, Listening Ports table, and Connections table");

shortest("On the Firewall page, verify the Listening Ports table shows at least one port with a port number and process name");
