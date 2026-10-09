package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import site.shadowcypher.app.data.AiChatMessage
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiChatScreen(viewModel: GuardianViewModel) {
    val messages by viewModel.chatMessages.collectAsState()
    val isLoading by viewModel.isAiLoading.collectAsState()
    val aiError by viewModel.aiError.collectAsState()
    val apiKey by viewModel.apiKey.collectAsState()

    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ColorBackground)
    ) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(ColorSurface)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    "Shadow AI",
                    color = ColorTextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 16.sp,
                    fontFamily = FontFamily.Monospace
                )
                Text(
                    "Security advisor",
                    color = ColorTextSecondary,
                    fontSize = 11.sp
                )
            }
            if (messages.isNotEmpty()) {
                IconButton(onClick = { viewModel.clearAiChat() }) {
                    Icon(Icons.Default.Delete, contentDescription = "Clear chat", tint = ColorTextSecondary)
                }
            }
        }

        Divider(color = ColorBorder, thickness = 1.dp)

        // No API key state
        if (apiKey.isBlank()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("No API key configured", color = ColorTextPrimary, fontWeight = FontWeight.Medium)
                    Text("Add your ShadowCypher key in Settings", color = ColorTextSecondary, fontSize = 13.sp)
                }
            }
            return
        }

        // Error banner
        aiError?.let { err ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(ColorCritical.copy(alpha = 0.12f))
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(err, color = ColorCritical, fontSize = 13.sp, modifier = Modifier.weight(1f))
                TextButton(onClick = { viewModel.dismissAiError() }) {
                    Text("Dismiss", color = ColorCritical, fontSize = 12.sp)
                }
            }
        }

        // Message list
        if (messages.isEmpty() && !isLoading) {
            Box(modifier = Modifier.weight(1f), contentAlignment = Alignment.Center) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.padding(32.dp)
                ) {
                    Text(
                        "Ask Shadow anything about your network",
                        color = ColorTextSecondary,
                        fontSize = 14.sp,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    listOf(
                        "Are there any active threats?",
                        "What devices are on my network?",
                        "Summarize recent incidents"
                    ).forEach { suggestion ->
                        SuggestionChip(
                            onClick = {
                                viewModel.sendAiMessage(suggestion)
                                scope.launch { }
                            },
                            label = { Text(suggestion, fontSize = 12.sp) },
                            colors = SuggestionChipDefaults.suggestionChipColors(
                                containerColor = ColorSurfaceVariant,
                                labelColor = ColorTextSecondary
                            ),
                            border = SuggestionChipDefaults.suggestionChipBorder(enabled = true, borderColor = ColorBorder)
                        )
                    }
                }
            }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(vertical = 12.dp)
            ) {
                items(messages) { msg ->
                    ChatBubble(msg)
                }
                if (isLoading) {
                    item {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(start = 4.dp),
                            horizontalArrangement = Arrangement.Start
                        ) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(12.dp, 12.dp, 12.dp, 4.dp))
                                    .background(ColorSurfaceVariant)
                                    .border(1.dp, ColorBorder, RoundedCornerShape(12.dp, 12.dp, 12.dp, 4.dp))
                                    .padding(horizontal = 14.dp, vertical = 10.dp)
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    strokeWidth = 2.dp,
                                    color = ColorAccentPurple
                                )
                            }
                        }
                    }
                }
            }
        }

        // Input bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(ColorSurface)
                .border(width = 1.dp, color = ColorBorder, shape = RoundedCornerShape(0.dp))
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                modifier = Modifier.weight(1f),
                placeholder = {
                    Text("Ask Shadow…", color = ColorTextSecondary, fontSize = 14.sp)
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ColorAccentPurple,
                    unfocusedBorderColor = ColorBorder,
                    focusedTextColor = ColorTextPrimary,
                    unfocusedTextColor = ColorTextPrimary,
                    cursorColor = ColorAccentPurple,
                    focusedContainerColor = ColorSurfaceVariant,
                    unfocusedContainerColor = ColorSurfaceVariant
                ),
                shape = RoundedCornerShape(10.dp),
                maxLines = 4,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = {
                    if (inputText.isNotBlank() && !isLoading) {
                        viewModel.sendAiMessage(inputText)
                        inputText = ""
                    }
                }),
                textStyle = LocalTextStyle.current.copy(fontSize = 14.sp)
            )
            IconButton(
                onClick = {
                    if (inputText.isNotBlank() && !isLoading) {
                        viewModel.sendAiMessage(inputText)
                        inputText = ""
                    }
                },
                enabled = inputText.isNotBlank() && !isLoading,
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (inputText.isNotBlank() && !isLoading) ColorAccentPurple else ColorSurfaceVariant)
            ) {
                Icon(
                    Icons.Default.Send,
                    contentDescription = "Send",
                    tint = if (inputText.isNotBlank() && !isLoading) Color.White else ColorTextSecondary,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}

@Composable
private fun ChatBubble(msg: AiChatMessage) {
    val isUser = msg.role == "user"
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 300.dp)
                .clip(
                    if (isUser) RoundedCornerShape(12.dp, 12.dp, 4.dp, 12.dp)
                    else RoundedCornerShape(12.dp, 12.dp, 12.dp, 4.dp)
                )
                .background(
                    if (isUser) ColorAccentPurpleContainer
                    else ColorSurfaceVariant
                )
                .border(
                    1.dp,
                    if (isUser) ColorAccentPurple.copy(alpha = 0.3f) else ColorBorder,
                    if (isUser) RoundedCornerShape(12.dp, 12.dp, 4.dp, 12.dp)
                    else RoundedCornerShape(12.dp, 12.dp, 12.dp, 4.dp)
                )
                .padding(horizontal = 14.dp, vertical = 10.dp)
        ) {
            Text(
                text = msg.content,
                color = if (isUser) ColorAccentPurple else ColorTextPrimary,
                fontSize = 14.sp,
                lineHeight = 20.sp
            )
        }
    }
}
