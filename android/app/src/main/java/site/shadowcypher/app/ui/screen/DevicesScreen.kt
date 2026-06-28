package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import site.shadowcypher.app.data.CveAlert
import site.shadowcypher.app.data.Device
import site.shadowcypher.app.data.GuardianSummary
import site.shadowcypher.app.data.Incident
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DevicesScreen(viewModel: GuardianViewModel) {
    val summary by viewModel.summary.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val pullState = rememberPullToRefreshState()
    var selectedDevice by remember { mutableStateOf<Device?>(null) }

    selectedDevice?.let { device ->
        DeviceDetailSheet(
            device = device,
            summary = summary,
            onDismiss = { selectedDevice = null }
        )
    }

    PullToRefreshBox(
        isRefreshing = isLoading,
        onRefresh = { viewModel.refresh() },
        state = pullState,
        modifier = Modifier
            .fillMaxSize()
            .background(ColorBackground)
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "NETWORK",
                            color = ColorAccentPurple,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 2.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Devices",
                            color = ColorTextPrimary,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    summary?.let {
                        Text(
                            text = "${it.devices.size} found",
                            color = ColorTextSecondary,
                            fontSize = 13.sp
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
            }

            val devices = summary?.devices ?: emptyList()
            if (devices.isEmpty() && !isLoading) {
                item {
                    EmptyState("No devices discovered yet.\nTrigger a scan from the dashboard.")
                }
            } else {
                items(devices, key = { it.mac ?: it.ip ?: it.hashCode().toString() }) { device ->
                    DeviceCard(device, onClick = { selectedDevice = device })
                }
            }

            item { Spacer(Modifier.height(80.dp)) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DeviceDetailSheet(
    device: Device,
    summary: GuardianSummary?,
    onDismiss: () -> Unit
) {
    val deviceKey = device.ip ?: device.hostname ?: device.mac
    val relatedCves = summary?.cve_alerts?.filter { cve ->
        cve.affected_device != null && deviceKey != null &&
                (cve.affected_device.contains(deviceKey, ignoreCase = true) ||
                 deviceKey.contains(cve.affected_device, ignoreCase = true))
    } ?: emptyList()
    val relatedIncidents = summary?.incidents?.filter { inc ->
        val desc = (inc.description ?: "") + (inc.type ?: "")
        deviceKey != null && desc.contains(deviceKey, ignoreCase = true)
    } ?: emptyList()

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = ColorSurface,
        tonalElevation = 0.dp
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 40.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column {
                    Text(
                        text = device.hostname ?: device.ip ?: "Unknown Device",
                        color = ColorTextPrimary,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    device.ip?.let {
                        Text(
                            text = it,
                            color = ColorAccentPurple,
                            fontSize = 13.sp,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
                device.status?.let { status ->
                    val color = if (status.uppercase() == "ALERT") ColorCritical else ColorLow
                    StatusChip(status, color)
                }
            }

            Spacer(Modifier.height(20.dp))
            HorizontalDivider(color = ColorBorder, thickness = 0.5.dp)
            Spacer(Modifier.height(16.dp))

            // Device details grid
            Text(
                text = "DEVICE INFO",
                color = ColorTextSecondary,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 2.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(10.dp))

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                if (!device.mac.isNullOrBlank())
                    DeviceDetailItem("MAC", device.mac, modifier = Modifier.weight(1f))
                if (!device.vendor.isNullOrBlank())
                    DeviceDetailItem("VENDOR", device.vendor, modifier = Modifier.weight(1f))
            }
            Spacer(Modifier.height(10.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                if (!device.os.isNullOrBlank())
                    DeviceDetailItem("TYPE", device.os, modifier = Modifier.weight(1f))
                if (!device.ip.isNullOrBlank())
                    DeviceDetailItem("IP", device.ip, modifier = Modifier.weight(1f))
            }

            // CVE matches
            if (relatedCves.isNotEmpty()) {
                Spacer(Modifier.height(20.dp))
                HorizontalDivider(color = ColorBorder, thickness = 0.5.dp)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = "CVE ALERTS (${relatedCves.size})",
                    color = ColorCritical,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 2.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                relatedCves.forEach { cve ->
                    CveRow(cve)
                    Spacer(Modifier.height(6.dp))
                }
            } else {
                Spacer(Modifier.height(16.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(ColorLow.copy(alpha = 0.08f), RoundedCornerShape(8.dp))
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "● No CVE alerts matched to this device",
                        color = ColorLow,
                        fontSize = 13.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }

            // Related incidents
            if (relatedIncidents.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                HorizontalDivider(color = ColorBorder, thickness = 0.5.dp)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = "RELATED INCIDENTS (${relatedIncidents.size})",
                    color = ColorHigh,
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 2.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                relatedIncidents.forEach { inc ->
                    IncidentMiniRow(inc)
                    Spacer(Modifier.height(6.dp))
                }
            }
        }
    }
}

@Composable
private fun CveRow(cve: CveAlert) {
    val severityColor = when (cve.severity?.uppercase()) {
        "CRITICAL" -> ColorCritical
        "HIGH" -> ColorHigh
        "MEDIUM" -> ColorMedium
        else -> ColorLow
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(ColorBackground, RoundedCornerShape(8.dp))
            .border(1.dp, severityColor.copy(alpha = 0.25f), RoundedCornerShape(8.dp))
            .padding(10.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .width(3.dp)
                .height(36.dp)
                .background(severityColor, RoundedCornerShape(2.dp))
        )
        Spacer(Modifier.width(10.dp))
        Column {
            Text(
                text = cve.cve_id,
                color = severityColor,
                fontSize = 12.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold
            )
            cve.description?.let {
                Text(
                    text = it,
                    color = ColorTextSecondary,
                    fontSize = 12.sp,
                    maxLines = 2
                )
            }
        }
    }
}

@Composable
private fun IncidentMiniRow(incident: Incident) {
    val severityColor = when (incident.severity?.uppercase()) {
        "CRITICAL" -> ColorCritical
        "HIGH" -> ColorHigh
        "MEDIUM" -> ColorMedium
        else -> ColorLow
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(ColorBackground, RoundedCornerShape(8.dp))
            .padding(10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        SeverityBadge(incident.severity.orEmpty())
        Spacer(Modifier.width(8.dp))
        Text(
            text = incident.description ?: incident.type ?: "Unknown incident",
            color = ColorTextSecondary,
            fontSize = 12.sp,
            maxLines = 2,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun DeviceCard(device: Device, onClick: () -> Unit) {
    val isAlert = device.status?.uppercase() == "ALERT"
    val statusColor = if (isAlert) ColorCritical else ColorLow

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, ColorBorder, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = ColorSurface),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = device.ip ?: device.mac ?: "—",
                        color = ColorAccentPurple,
                        fontSize = 14.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = device.hostname ?: "Unknown host",
                        color = ColorTextPrimary,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
                device.status?.let { status ->
                    StatusChip(status, statusColor)
                }
            }

            Spacer(Modifier.height(10.dp))
            HorizontalDivider(color = ColorBorder, thickness = 0.5.dp)
            Spacer(Modifier.height(10.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                device.os?.let { DeviceDetailItem("OS", it) }
                device.vendor?.let { DeviceDetailItem("VENDOR", it) }
                device.mac?.let { DeviceDetailItem("MAC", it) }
            }

            Spacer(Modifier.height(8.dp))
            Text(
                text = "TAP FOR DETAILS",
                color = ColorTextSecondary.copy(alpha = 0.4f),
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 1.sp
            )
        }
    }
}

@Composable
private fun StatusChip(status: String, color: Color) {
    Box(
        modifier = Modifier
            .background(color.copy(alpha = 0.15f), RoundedCornerShape(6.dp))
            .border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(
            text = status.uppercase(),
            color = color,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp
        )
    }
}

@Composable
private fun DeviceDetailItem(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(
            text = label,
            color = ColorTextSecondary,
            fontSize = 9.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 1.sp
        )
        Text(
            text = value,
            color = ColorTextPrimary,
            fontSize = 12.sp,
            fontFamily = FontFamily.Monospace
        )
    }
}

@Composable
private fun EmptyState(message: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(200.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = message,
            color = ColorTextSecondary,
            fontSize = 14.sp,
            textAlign = TextAlign.Center
        )
    }
}
