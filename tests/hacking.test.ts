import { shortest } from "@antiwork/shortest";

// Hacking / Pentesting Suite
shortest("Log in with 'admin'/'shadow', click 'Hacking' in the sidebar, and verify the page shows 'Hacking / Pentesting Suite' heading with Shadow Mode toggle, target input, and offensive tool buttons: Web Stress, Slowloris, Nikto, Nmap Vuln, Gobuster, SQLMap, Flood, Wifite, and Searchsploit");

shortest("On the Hacking page, verify the Output Console shows the warning text 'USE FOR AUTHORIZED TESTING ONLY'");

shortest("On the Hacking page, type 'apache' in the target field, click 'Searchsploit', and verify the output console shows exploit database search results — not an error");

shortest("On the Hacking page, toggle the Shadow Mode switch and verify the status text changes to 'SHADOW: ON'");
