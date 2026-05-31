package site.shadowcypher.app.ui.screen

import site.shadowcypher.app.BuildConfig
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: GuardianViewModel) {
    val me by viewModel.me.collectAsState()
    val currentKey by viewModel.apiKey.collectAsState()

    var draftKey by remember(currentKey) { mutableStateOf(currentKey) }
    var showKey by remember { mutableStateOf(false) }
    var saved by remember { mutableStateOf(false) }
    val keyboardController = LocalSoftwareKeyboardController.current

    fun saveKey() {
        keyboardController?.hide()
        viewModel.setApiKey(draftKey.trim())
        saved = true
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ColorBackground)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        Text(
            text = "CONFIGURATION",
            color = ColorAccentPurple,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 2.sp,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Settings",
            color = ColorTextPrimary,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold
        )

        Spacer(Modifier.height(20.dp))

        // Account section
        me?.let { user ->
            SectionCard {
                SectionCardLabel("ACCOUNT")
                Spacer(Modifier.height(12.dp))
                DetailRow("Email", user.email)
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    DetailRow("Plan", user.effective_plan.uppercase(), modifier = Modifier.weight(1f))
                    PlanBadge(user.effective_plan, user.in_trial, user.trial_days_remaining)
                }
            }
            Spacer(Modifier.height(12.dp))
        }

        // API Key section
        SectionCard {
            SectionCardLabel("API KEY")
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = draftKey,
                onValueChange = {
                    draftKey = it
                    saved = false
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Bearer token", color = ColorTextSecondary) },
                placeholder = { Text("sc_live_...", color = ColorTextSecondary.copy(alpha = 0.5f), fontFamily = FontFamily.Monospace) },
                visualTransformation = if (showKey) VisualTransformation.None else PasswordVisualTransformation(),
                trailingIcon = {
                    IconButton(onClick = { showKey = !showKey }) {
                        Icon(
                            imageVector = if (showKey) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                            contentDescription = if (showKey) "Hide key" else "Show key",
                            tint = ColorTextSecondary
                        )
                    }
                },
                keyboardOptions = KeyboardOptions(
                    keyboardType = KeyboardType.Password,
                    imeAction = ImeAction.Done
                ),
                keyboardActions = KeyboardActions(onDone = { saveKey() }),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ColorAccentPurple,
                    unfocusedBorderColor = ColorBorder,
                    focusedTextColor = ColorTextPrimary,
                    unfocusedTextColor = ColorTextPrimary,
                    cursorColor = ColorAccentPurple,
                    focusedContainerColor = ColorSurfaceVariant,
                    unfocusedContainerColor = ColorSurfaceVariant
                ),
                singleLine = true
            )
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = { saveKey() },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ColorAccentPurple),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (saved) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Saved", fontWeight = FontWeight.Bold)
                    } else {
                        Text("Save Key", fontWeight = FontWeight.Bold)
                    }
                }
                if (currentKey.isNotBlank()) {
                    OutlinedButton(
                        onClick = {
                            draftKey = ""
                            saved = false
                            viewModel.clearApiKey()
                        },
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = ColorCritical),
                        border = androidx.compose.foundation.BorderStroke(1.dp, ColorCritical.copy(alpha = 0.5f)),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Clear", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        Spacer(Modifier.height(12.dp))

        // Agent install instructions
        SectionCard {
            SectionCardLabel("INSTALL AGENT")
            Spacer(Modifier.height(12.dp))
            Text(
                text = "To monitor your network, install the ShadowCypher Guardian agent on a Linux host:",
                color = ColorTextSecondary,
                fontSize = 13.sp
            )
            Spacer(Modifier.height(10.dp))
            CodeBlock("curl -sSL https://shadowcypher.site/install.sh | bash")
            Spacer(Modifier.height(8.dp))
            Text(
                text = "The agent will auto-register and appear in your dashboard.",
                color = ColorTextSecondary,
                fontSize = 12.sp
            )
        }

        Spacer(Modifier.height(12.dp))

        // App info
        SectionCard {
            SectionCardLabel("ABOUT")
            Spacer(Modifier.height(12.dp))
            DetailRow("Version", BuildConfig.VERSION_NAME)
            Spacer(Modifier.height(4.dp))
            DetailRow("API", "api.shadowcypher.site")
            Spacer(Modifier.height(4.dp))
            DetailRow("Platform", "Native Android")
        }

        Spacer(Modifier.height(80.dp))
    }
}

@Composable
private fun SectionCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, ColorBorder, RoundedCornerShape(10.dp)),
        colors = CardDefaults.cardColors(containerColor = ColorSurface),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), content = content)
    }
}

@Composable
private fun SectionCardLabel(text: String) {
    Text(
        text = text,
        color = ColorTextSecondary,
        fontSize = 10.sp,
        fontFamily = FontFamily.Monospace,
        letterSpacing = 2.sp,
        fontWeight = FontWeight.Bold
    )
}

@Composable
private fun DetailRow(label: String, value: String, modifier: Modifier = Modifier) {
    Row(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            text = label,
            color = ColorTextSecondary,
            fontSize = 13.sp,
            modifier = Modifier.width(70.dp)
        )
        Text(
            text = value,
            color = ColorTextPrimary,
            fontSize = 13.sp,
            fontFamily = if (label == "API") FontFamily.Monospace else FontFamily.Default
        )
    }
}

@Composable
private fun PlanBadge(plan: String, inTrial: Boolean, trialDays: Int?) {
    val label = buildString {
        append(plan.uppercase())
        if (inTrial && trialDays != null) append(" • ${trialDays}d left")
    }
    Box(
        modifier = Modifier
            .background(ColorAccentPurple.copy(alpha = 0.15f), RoundedCornerShape(6.dp))
            .border(1.dp, ColorAccentPurple.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(
            text = label,
            color = ColorAccentPurple,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun CodeBlock(code: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF0D0D10), RoundedCornerShape(6.dp))
            .border(1.dp, ColorBorder, RoundedCornerShape(6.dp))
            .padding(10.dp)
    ) {
        Text(
            text = code,
            color = ColorLow,
            fontSize = 12.sp,
            fontFamily = FontFamily.Monospace
        )
    }
}
