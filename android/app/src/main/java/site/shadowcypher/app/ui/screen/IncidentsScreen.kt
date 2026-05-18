package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import site.shadowcypher.app.data.Incident
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IncidentsScreen(viewModel: GuardianViewModel) {
    val summary by viewModel.summary.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val pullState = rememberPullToRefreshState()

    val incidents = summary?.incidents ?: emptyList()
    val (unresolved, resolved) = incidents.partition { !it.resolved }

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
                Column {
                    Text(
                        text = "SECURITY",
                        color = ColorAccentPurple,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        letterSpacing = 2.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Incidents",
                            color = ColorTextPrimary,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold
                        )
                        if (unresolved.isNotEmpty()) {
                            Box(
                                modifier = Modifier
                                    .background(ColorCritical.copy(alpha = 0.15f), RoundedCornerShape(6.dp))
                                    .border(1.dp, ColorCritical.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                                    .padding(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text(
                                    text = "${unresolved.size} ACTIVE",
                                    color = ColorCritical,
                                    fontSize = 10.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    letterSpacing = 0.5.sp
                                )
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }

            if (incidents.isEmpty() && !isLoading) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No incidents detected.\nYour network looks clean.",
                            color = ColorTextSecondary,
                            fontSize = 14.sp,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                }
            }

            if (unresolved.isNotEmpty()) {
                item {
                    SectionDividerLabel("ACTIVE")
                    Spacer(Modifier.height(4.dp))
                }
                items(unresolved, key = { it.id }) { incident ->
                    IncidentRow(incident, dimmed = false)
                }
            }

            if (resolved.isNotEmpty()) {
                item {
                    Spacer(Modifier.height(8.dp))
                    SectionDividerLabel("RESOLVED")
                    Spacer(Modifier.height(4.dp))
                }
                items(resolved, key = { it.id }) { incident ->
                    IncidentRow(incident, dimmed = true)
                }
            }

            item { Spacer(Modifier.height(80.dp)) }
        }
    }
}

@Composable
private fun SectionDividerLabel(text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = text,
            color = ColorTextSecondary,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 2.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.width(8.dp))
        Divider(
            modifier = Modifier.weight(1f),
            color = ColorBorder,
            thickness = 0.5.dp
        )
    }
}

@Composable
private fun IncidentRow(incident: Incident, dimmed: Boolean) {
    val alpha = if (dimmed) 0.45f else 1f
    val severityColor = when (incident.severity.orEmpty().uppercase()) {
        "CRITICAL" -> ColorCritical
        "HIGH" -> ColorHigh
        "MEDIUM" -> ColorMedium
        else -> ColorLow
    }.copy(alpha = alpha)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, ColorBorder, RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = ColorSurface),
        shape = RoundedCornerShape(10.dp)
    ) {
        Row(modifier = Modifier.padding(14.dp)) {
            // Severity stripe
            Box(
                modifier = Modifier
                    .width(3.dp)
                    .heightIn(min = 44.dp)
                    .background(severityColor, RoundedCornerShape(2.dp))
                    .align(Alignment.CenterVertically)
            )
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    SeverityBadge(incident.severity.orEmpty())
                    if (incident.resolved) {
                        Box(
                            modifier = Modifier
                                .background(ColorLow.copy(alpha = 0.1f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 5.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = "RESOLVED",
                                color = ColorLow.copy(alpha = 0.7f),
                                fontSize = 9.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 0.5.sp
                            )
                        }
                    }
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    text = incident.type.orEmpty(),
                    color = ColorTextPrimary.copy(alpha = alpha),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = incident.description.orEmpty(),
                    color = ColorTextSecondary.copy(alpha = alpha),
                    fontSize = 13.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = incident.created_at.take(16).replace("T", "  "),
                    color = ColorTextSecondary.copy(alpha = alpha * 0.7f),
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
        }
    }
}
