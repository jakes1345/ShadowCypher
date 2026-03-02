import { shortest } from "@antiwork/shortest";

// Black Ops Intelligence
shortest("Log in with 'admin'/'shadow', click 'Intelligence' in the sidebar, and verify the page shows Signal Intercept, Wireless Recon, Global Threat Intel, Data Breach Monitor, Darknet Acquisition, and IDS / Audit Logs sections");

shortest("On the Intelligence page, click 'Fetch Feed' in the Global Threat Intel section and verify that threat IP addresses appear from abuse.ch or ipsum sources — not placeholder data");

shortest("On the Intelligence page, click 'Sync IDS' and verify the IDS / Audit Logs section updates with content (either real alerts or 'No IDS alerts')");

shortest("On the Intelligence page, click '⚙️ Intel Config' and verify a modal appears with a field for HIBP API key");
