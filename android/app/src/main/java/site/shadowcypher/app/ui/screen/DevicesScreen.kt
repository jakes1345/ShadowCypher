package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import site.shadowcypher.app.data.Device
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DevicesScreen(viewModel: GuardianViewModel) {
    val summary by viewModel.summary.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val pullState = rememberPullToRefreshState()

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
                items(devices, key = { it.ip }) { device ->
                    DeviceCard(device)
                }
            }

            item { Spacer(Modifier.height(80.dp)) }
        }
    }
}

@Composable
private fun DeviceCard(device: Device) {
    val isAlert = device.status?.uppercase() == "ALERT"
    val statusColor = if (isAlert) ColorCritical else ColorLow

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, ColorBorder, RoundedCornerShape(10.dp)),
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
                        text = device.ip,
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
            Divider(color = ColorBorder, thickness = 0.5.dp)
            Spacer(Modifier.height(10.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                device.os?.let { DeviceDetailItem("OS", it) }
                device.vendor?.let { DeviceDetailItem("VENDOR", it) }
                device.mac?.let { DeviceDetailItem("MAC", it) }
            }
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
private fun DeviceDetailItem(label: String, value: String) {
    Column {
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
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
    }
}
