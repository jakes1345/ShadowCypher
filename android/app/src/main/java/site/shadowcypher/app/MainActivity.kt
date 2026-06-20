package site.shadowcypher.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Hub
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import site.shadowcypher.app.service.BackgroundSyncWorker
import site.shadowcypher.app.service.NotificationHelper
import site.shadowcypher.app.ui.screen.DashboardScreen
import site.shadowcypher.app.ui.screen.DevicesScreen
import site.shadowcypher.app.ui.screen.EcosystemScreen
import site.shadowcypher.app.ui.screen.IncidentsScreen
import site.shadowcypher.app.ui.screen.MissionsScreen
import site.shadowcypher.app.ui.screen.SettingsScreen
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

sealed class NavRoute(val route: String, val label: String, val icon: ImageVector) {
    object Dashboard : NavRoute("dashboard", "Dashboard", Icons.Default.Dashboard)
    object Devices : NavRoute("devices", "Devices", Icons.Default.Devices)
    object Incidents : NavRoute("incidents", "Incidents", Icons.Default.Warning)
    object Missions : NavRoute("missions", "Missions", Icons.Default.PlayArrow)
    object Ecosystem : NavRoute("ecosystem", "Ecosystem", Icons.Default.Hub)
    object Settings : NavRoute("settings", "Settings", Icons.Default.Settings)
}

private val navItems = listOf(
    NavRoute.Dashboard,
    NavRoute.Devices,
    NavRoute.Incidents,
    NavRoute.Missions,
    NavRoute.Ecosystem,
    NavRoute.Settings
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        NotificationHelper.createChannels(this)
        BackgroundSyncWorker.schedule(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1001)
        }

        setContent {
            ShadowGuardianApp()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShadowGuardianApp() {
    GuardianTheme {
        val navController = rememberNavController()
        val viewModel: GuardianViewModel = viewModel()

        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(ColorBackground),
            containerColor = ColorBackground,
            bottomBar = {
                NavigationBar(
                    containerColor = ColorSurface,
                    tonalElevation = 0.dp
                ) {
                    val navBackStackEntry by navController.currentBackStackEntryAsState()
                    val currentDestination = navBackStackEntry?.destination

                    navItems.forEach { item ->
                        val selected = currentDestination?.hierarchy?.any { it.route == item.route } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(item.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                Icon(item.icon, contentDescription = item.label)
                            },
                            label = {
                                Text(item.label, style = MaterialTheme.typography.labelSmall)
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = ColorAccentPurple,
                                selectedTextColor = ColorAccentPurple,
                                unselectedIconColor = ColorTextSecondary,
                                unselectedTextColor = ColorTextSecondary,
                                indicatorColor = ColorAccentPurple.copy(alpha = 0.12f)
                            )
                        )
                    }
                }
            }
        ) { innerPadding ->
            NavHost(
                navController = navController,
                startDestination = NavRoute.Dashboard.route,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                composable(NavRoute.Dashboard.route) {
                    DashboardScreen(
                        viewModel = viewModel,
                        onNavigateToSettings = {
                            navController.navigate(NavRoute.Settings.route) {
                                launchSingleTop = true
                            }
                        }
                    )
                }
                composable(NavRoute.Devices.route) {
                    DevicesScreen(viewModel = viewModel)
                }
                composable(NavRoute.Incidents.route) {
                    IncidentsScreen(viewModel = viewModel)
                }
                composable(NavRoute.Missions.route) {
                    MissionsScreen(viewModel = viewModel)
                }
                composable(NavRoute.Ecosystem.route) {
                    EcosystemScreen()
                }
                composable(NavRoute.Settings.route) {
                    SettingsScreen(viewModel = viewModel)
                }
            }
        }
    }
}
