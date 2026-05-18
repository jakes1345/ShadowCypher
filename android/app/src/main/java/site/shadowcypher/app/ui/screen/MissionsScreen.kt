package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
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

    LaunchedEffect(Unit) {
        viewModel.loadAgents()
        viewModel.loadMissions()
    }

    LaunchedEffect(agents) {
        if (selectedAgent == null && agents.isNotEmpty()) {
            selectedAgent = agents.first()
            viewModel.loadMissions(agents.first().hostname)
        }
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
            Text("Missions", style = MaterialTheme.typography.headlineSmall, color = ColorTextPrimary)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                IconButton(onClick = { viewModel.loadMissions(selectedAgent?.hostname) }) {
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

        if (missionStatus != null) {
            Spacer(Modifier.height(8.dp))
            Surface(
                color = ColorAccentPurple.copy(alpha = 0.12f),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    missionStatus ?: "",
                    modifier = Modifier.padding(10.dp),
                    style = MaterialTheme.typography.bodySmall,
                    color = ColorAccentPurple
                )
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
                    val agentId = selectedAgent?.hostname ?: return@MissionCompose
                    viewModel.submitMission(agentId, scriptText, labelText.ifBlank { null })
                    scriptText = ""
                    labelText = ""
                    showCompose = false
                }
            )
        }

        Spacer(Modifier.height(16.dp))

        if (missions.isEmpty()) {
            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text("No missions yet.", color = ColorTextSecondary, style = MaterialTheme.typography.bodyMedium)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(missions) { mission ->
                    MissionCard(mission = mission)
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
                                text = { Text(agent.hostname) },
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
                maxLines = 10,
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
private fun MissionCard(mission: Mission) {
    val statusColor = when (mission.status) {
        "completed" -> Color(0xFF22c55e)
        "failed"    -> Color(0xFFef4444)
        "running"   -> Color(0xFFf59e0b)
        else        -> ColorTextSecondary
    }

    Surface(color = ColorSurface, shape = RoundedCornerShape(12.dp)) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(mission.id, style = MaterialTheme.typography.labelMedium, color = ColorTextSecondary)
                Surface(color = statusColor.copy(alpha = 0.15f), shape = RoundedCornerShape(4.dp)) {
                    Text(
                        mission.status.uppercase(),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = statusColor
                    )
                }
            }
            Spacer(Modifier.height(4.dp))
            Text(mission.created_at, style = MaterialTheme.typography.bodySmall, color = ColorTextSecondary)
            if (!mission.result_output.isNullOrBlank()) {
                Spacer(Modifier.height(8.dp))
                Surface(color = ColorBackground, shape = RoundedCornerShape(6.dp)) {
                    Text(
                        mission.result_output.take(400),
                        modifier = Modifier.padding(8.dp),
                        style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                        color = ColorTextPrimary
                    )
                }
            }
        }
    }
}
