package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import site.shadowcypher.app.data.Agent
import site.shadowcypher.app.data.Mission
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@Composable
fun MissionsScreen(viewModel: GuardianViewModel) {
    val agents by viewModel.agents.collectAsState()
    val missions by viewModel.missions.collectAsState()
    val missionStatus by viewModel.missionStatus.collectAsState()

    var selectedAgent by remember { mutableStateOf<Agent?>(null) }
    var scriptText by remember { mutableStateOf("") }
    var labelText by remember { mutableStateOf("") }
    var showCompose by remember { mutableStateOf(false) }
    var outputMission by remember { mutableStateOf<Mission?>(null) }

    LaunchedEffect(Unit) {
        viewModel.loadAgents()
        viewModel.loadMissions()
    }

    LaunchedEffect(agents) {
        if (selectedAgent == null && agents.isNotEmpty()) {
            selectedAgent = agents.first()
            viewModel.loadMissions(agents.first().id)
        }
    }

    // Update outputMission when missions list refreshes (so live output shows)
    LaunchedEffect(missions) {
        outputMission?.let { current ->
            missions.find { it.id == current.id }?.let { updated ->
                outputMission = updated
            }
        }
    }

    // Full output dialog
    outputMission?.let { mission ->
        MissionOutputDialog(mission = mission, onDismiss = { outputMission = null })
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ColorBackground)
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    "REMOTE EXEC",
                    color = ColorAccentPurple,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 2.sp
                )
                Text("Missions", style = MaterialTheme.typography.headlineSmall, color = ColorTextPrimary)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                IconButton(onClick = { viewModel.loadMissions(selectedAgent?.id) }) {
                    Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = ColorAccentPurple)
                }
                IconButton(onClick = { showCompose = !showCompose }) {
                    Icon(Icons.Default.PlayArrow, contentDescription = "New mission", tint = ColorAccentPurple)
                }
            }
        }

        Spacer(Modifier.height(4.dp))
        Text(
            "Send ShadowScript to run on your desktop via the Guardian agent.",
            style = MaterialTheme.typography.bodySmall,
            color = ColorTextSecondary
        )

        missionStatus?.let { status ->
            Spacer(Modifier.height(8.dp))
            Surface(
                color = ColorAccentPurple.copy(alpha = 0.12f),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        status,
                        style = MaterialTheme.typography.bodySmall,
                        color = ColorAccentPurple,
                        modifier = Modifier.weight(1f)
                    )
                    TextButton(
                        onClick = { viewModel.clearMissionStatus() },
                        contentPadding = PaddingValues(horizontal = 4.dp)
                    ) {
                        Text("✕", color = ColorAccentPurple, fontSize = 12.sp)
                    }
                }
            }
        }

        if (showCompose) {
            Spacer(Modifier.height(12.dp))
            MissionCompose(
                agents = agents,
                selectedAgent = selectedAgent,
                onSelectAgent = { selectedAgent = it },
                script = scriptText,
                onScriptChange = { scriptText = it },
                label = labelText,
                onLabelChange = { labelText = it },
                onSubmit = {
                    val agentId = selectedAgent?.id ?: return@MissionCompose
                    viewModel.submitMission(agentId, scriptText, labelText.ifBlank { null })
                    scriptText = ""
                    labelText = ""
                    showCompose = false
                }
            )
        }

        Spacer(Modifier.height(16.dp))

        // Running missions indicator
        val running = missions.count { it.status == "running" || it.status == "queued" }
        if (running > 0) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFFf59e0b).copy(alpha = 0.1f), RoundedCornerShape(8.dp))
                    .border(1.dp, Color(0xFFf59e0b).copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(14.dp),
                    color = Color(0xFFf59e0b),
                    strokeWidth = 2.dp
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    "$running mission${if (running > 1) "s" else ""} running — auto-refreshing…",
                    color = Color(0xFFf59e0b),
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
            Spacer(Modifier.height(10.dp))
        }

        if (missions.isEmpty()) {
            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text("No missions yet.", color = ColorTextSecondary, style = MaterialTheme.typography.bodyMedium)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(missions, key = { it.id }) { mission ->
                    MissionCard(mission = mission, onClick = { outputMission = mission })
                }
            }
        }
    }
}

@Composable
private fun MissionCompose(
    agents: List<Agent>,
    selectedAgent: Agent?,
    onSelectAgent: (Agent) -> Unit,
    script: String,
    onScriptChange: (String) -> Unit,
    label: String,
    onLabelChange: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }

    Surface(color = ColorSurface, shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("New Mission", style = MaterialTheme.typography.titleSmall, color = ColorTextPrimary)

            if (agents.isNotEmpty()) {
                Box {
                    OutlinedButton(
                        onClick = { expanded = true },
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = ColorTextPrimary)
                    ) {
                        Text(selectedAgent?.hostname ?: "Select agent", style = MaterialTheme.typography.bodySmall)
                    }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        agents.forEach { agent ->
                            DropdownMenuItem(
                                text = {
                                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                        Box(
                                            modifier = Modifier
                                                .size(6.dp)
                                                .background(
                                                    if (agent.online) Color(0xFF22c55e) else ColorTextSecondary,
                                                    RoundedCornerShape(50)
                                                )
                                        )
                                        Text(agent.hostname)
                                    }
                                },
                                onClick = { onSelectAgent(agent); expanded = false }
                            )
                        }
                    }
                }
            }

            OutlinedTextField(
                value = label,
                onValueChange = onLabelChange,
                label = { Text("Label (optional)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ColorAccentPurple,
                    focusedLabelColor = ColorAccentPurple,
                    unfocusedBorderColor = ColorTextSecondary.copy(alpha = 0.4f),
                    cursorColor = ColorAccentPurple,
                    focusedTextColor = ColorTextPrimary,
                    unfocusedTextColor = ColorTextPrimary,
                )
            )

            OutlinedTextField(
                value = script,
                onValueChange = onScriptChange,
                label = { Text("ShadowScript") },
                minLines = 4,
                maxLines = 12,
                modifier = Modifier.fillMaxWidth(),
                textStyle = TextStyle(fontFamily = FontFamily.Monospace),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ColorAccentPurple,
                    focusedLabelColor = ColorAccentPurple,
                    unfocusedBorderColor = ColorTextSecondary.copy(alpha = 0.4f),
                    cursorColor = ColorAccentPurple,
                    focusedTextColor = ColorTextPrimary,
                    unfocusedTextColor = ColorTextPrimary,
                )
            )

            Button(
                onClick = onSubmit,
                enabled = script.isNotBlank() && selectedAgent != null,
                colors = ButtonDefaults.buttonColors(containerColor = ColorAccentPurple),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Submit Mission")
            }
        }
    }
}

@Composable
private fun MissionCard(mission: Mission, onClick: () -> Unit) {
    val statusColor = when (mission.status) {
        "completed" -> Color(0xFF22c55e)
        "failed"    -> Color(0xFFef4444)
        "running"   -> Color(0xFFf59e0b)
        "queued"    -> Color(0xFF94a3b8)
        else        -> ColorTextSecondary
    }
    val isRunning = mission.status == "running" || mission.status == "queued"

    Surface(
        color = ColorSurface,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    mission.id.take(16) + if (mission.id.length > 16) "…" else "",
                    style = MaterialTheme.typography.labelMedium,
                    color = ColorTextSecondary,
                    fontFamily = FontFamily.Monospace
                )
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (isRunning) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(10.dp),
                            color = statusColor,
                            strokeWidth = 1.5.dp
                        )
                    }
                    Surface(color = statusColor.copy(alpha = 0.15f), shape = RoundedCornerShape(4.dp)) {
                        Text(
                            mission.status.uppercase(),
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                            style = MaterialTheme.typography.labelSmall,
                            color = statusColor
                        )
                    }
                }
            }
            Spacer(Modifier.height(4.dp))
            mission.exit_code?.let { code ->
                Text(
                    "exit ${code}",
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    color = if (code == 0) Color(0xFF22c55e) else Color(0xFFef4444)
                )
                Spacer(Modifier.height(2.dp))
            }
            Text(mission.created_at.take(16).replace("T", "  "), style = MaterialTheme.typography.bodySmall, color = ColorTextSecondary)
            mission.completed_at?.let {
                Text("done ${it.take(16).replace("T", "  ")}", style = MaterialTheme.typography.bodySmall, color = ColorTextSecondary)
            }
            if (!mission.result_output.isNullOrBlank()) {
                Spacer(Modifier.height(8.dp))
                Surface(color = ColorBackground, shape = RoundedCornerShape(6.dp)) {
                    Column(modifier = Modifier.padding(8.dp)) {
                        Text(
                            mission.result_output.take(200) + if (mission.result_output.length > 200) "\n…" else "",
                            style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                            color = ColorTextPrimary
                        )
                        if (mission.result_output.length > 200) {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                "TAP TO VIEW FULL OUTPUT",
                                fontSize = 9.sp,
                                fontFamily = FontFamily.Monospace,
                                letterSpacing = 1.sp,
                                color = ColorAccentPurple
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MissionOutputDialog(mission: Mission, onDismiss: () -> Unit) {
    val statusColor = when (mission.status) {
        "completed" -> Color(0xFF22c55e)
        "failed"    -> Color(0xFFef4444)
        "running"   -> Color(0xFFf59e0b)
        else        -> ColorTextSecondary
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            color = ColorBackground,
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            "MISSION OUTPUT",
                            color = ColorAccentPurple,
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 2.sp
                        )
                        Text(
                            mission.id,
                            color = ColorTextSecondary,
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Surface(color = statusColor.copy(alpha = 0.15f), shape = RoundedCornerShape(4.dp)) {
                            Text(
                                mission.status.uppercase(),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                color = statusColor,
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                        IconButton(onClick = onDismiss) {
                            Icon(Icons.Default.Close, contentDescription = "Close", tint = ColorTextSecondary)
                        }
                    }
                }

                mission.exit_code?.let { code ->
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "exit code: $code",
                        color = if (code == 0) Color(0xFF22c55e) else Color(0xFFef4444),
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }

                Spacer(Modifier.height(12.dp))
                HorizontalDivider(color = ColorBorder, thickness = 0.5.dp)
                Spacer(Modifier.height(12.dp))

                val isRunning = mission.status == "running" || mission.status == "queued"
                if (isRunning) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.padding(bottom = 12.dp)
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            color = Color(0xFFf59e0b),
                            strokeWidth = 2.dp
                        )
                        Text(
                            "Running… output will appear here",
                            color = Color(0xFFf59e0b),
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }

                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(ColorSurface, RoundedCornerShape(8.dp))
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(12.dp)
                    ) {
                        if (mission.result_output.isNullOrBlank()) {
                            Text(
                                if (isRunning) "Waiting for output…" else "No output produced.",
                                color = ColorTextSecondary,
                                fontSize = 13.sp,
                                fontFamily = FontFamily.Monospace
                            )
                        } else {
                            Text(
                                mission.result_output,
                                color = ColorTextPrimary,
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                lineHeight = 18.sp
                            )
                        }
                    }
                }
            }
        }
    }
}
