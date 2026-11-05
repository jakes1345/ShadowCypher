cmake_minimum_required(VERSION 3.16)
project(ShadowCypher VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Network Concurrent WebSockets)
find_package(OpenSSL REQUIRED)
include(CTest)
include(GNUInstallDirs)
add_subdirectory(core)
add_subdirectory(daemon)

qt_add_executable(shadowcypher
    src/main.cpp
    src/api/ApiClient.cpp
    src/api/ApiClient.h
    src/LoginDialog.cpp
    src/LoginDialog.h
    src/MainWindow.cpp
    src/MainWindow.h
    src/theme.h
    src/ipc/IpcClient.cpp
    src/ipc/IpcClient.h
    src/widgets/ArcGauge.cpp
    src/widgets/ArcGauge.h
    src/widgets/MiniStat.cpp
    src/widgets/MiniStat.h
    src/widgets/TacticalTerminal.cpp
    src/widgets/TacticalTerminal.h
    src/pages/DashboardPage.cpp
    src/pages/DashboardPage.h
    src/pages/GuardianPage.cpp
    src/pages/GuardianPage.h
    src/pages/CounterIntelPage.cpp
    src/pages/CounterIntelPage.h
    src/pages/ArsenalPage.cpp
    src/pages/ArsenalPage.h
    src/pages/AiPage.cpp
    src/pages/AiPage.h
    src/pages/ShadowScriptPage.cpp
    src/pages/ShadowScriptPage.h
    src/pages/ChatPage.cpp
    src/pages/ChatPage.h
    src/pages/MailPage.cpp
    src/pages/MailPage.h
    src/pages/DrivePage.cpp
    src/pages/DrivePage.h
    src/pages/CalendarPage.cpp
    src/pages/CalendarPage.h
    src/pages/GhostPage.cpp
    src/pages/GhostPage.h
    src/pages/CveFeedPage.cpp
    src/pages/CveFeedPage.h
    src/pages/OsintPage.cpp
    src/pages/OsintPage.h
    src/pages/SettingsPage.cpp
    src/pages/SettingsPage.h
    src/pages/NetworkPage.cpp
    src/pages/NetworkPage.h
    src/pages/ThreatPage.cpp
    src/pages/ThreatPage.h
    src/pages/VulnPage.cpp
    src/pages/VulnPage.h
    src/privacy/PrivacyHelper.cpp
    src/privacy/PrivacyHelper.h
)

target_link_libraries(shadowcypher PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::Network
    Qt6::Concurrent
    Qt6::WebSockets
    OpenSSL::Crypto
    shadow_runtime
)
add_dependencies(shadowcypher shadowcypher-daemon)

if(NOT MSVC)
    target_compile_options(shadowcypher PRIVATE -Wall -Wextra -O2)
else()
    target_compile_options(shadowcypher PRIVATE /W3 /O2)
endif()

if(UNIX AND NOT APPLE)
    # Ghost mode's kill-switch: the only code that runs as root. Launched through
    # pkexec with a single fixed verb, and kept free of Qt so it stays small.
    add_executable(shadowcypher-privacy-helper privacy-helper/main.cpp)
    target_compile_options(shadowcypher-privacy-helper PRIVATE -Wall -Wextra)
    # Runs as root: no $ORIGIN-relative library search path.
    set_target_properties(shadowcypher-privacy-helper PROPERTIES INSTALL_RPATH "")
    add_dependencies(shadowcypher shadowcypher-privacy-helper)

    set(SC_PRIVACY_HELPER_PATH
        "${CMAKE_INSTALL_FULL_LIBEXECDIR}/shadowcypher/shadowcypher-privacy-helper")
    target_compile_definitions(shadowcypher PRIVATE
        SC_PRIVACY_HELPER="${SC_PRIVACY_HELPER_PATH}")

    # polkit only reads actions from /usr/share, whatever the install prefix.
    set(POLKIT_ACTIONS_DIR "/usr/share/polkit-1/actions" CACHE PATH "polkit actions directory")
    configure_file(packaging/linux/site.shadowcypher.privacy.policy.in
                   ${CMAKE_CURRENT_BINARY_DIR}/site.shadowcypher.privacy.policy @ONLY)

    install(TARGETS shadowcypher-privacy-helper
        RUNTIME DESTINATION ${CMAKE_INSTALL_LIBEXECDIR}/shadowcypher)
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/site.shadowcypher.privacy.policy
        DESTINATION ${POLKIT_ACTIONS_DIR})
endif()

install(TARGETS shadowcypher DESTINATION bin)
# Optional mission scripts for the ShadowScript page (searched at runtime too).
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../shadowscript/missions")
    install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../shadowscript/missions"
        DESTINATION share/shadowcypher)
endif()
install(FILES assets/shadowcypher.desktop DESTINATION share/applications)
install(FILES assets/icon-512.png
    DESTINATION share/icons/hicolor/512x512/apps
    RENAME shadowcypher.png)
