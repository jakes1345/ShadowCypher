cmake_minimum_required(VERSION 3.16)
project(ShadowCypher VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Network Concurrent)

qt_add_executable(shadowcypher
    src/main.cpp
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
    src/pages/PlaceholderPage.h
)

target_link_libraries(shadowcypher PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::Network
    Qt6::Concurrent
)

target_compile_options(shadowcypher PRIVATE -Wall -Wextra -O2)

install(TARGETS shadowcypher DESTINATION bin)
install(FILES assets/shadowcypher.desktop DESTINATION share/applications)
install(FILES assets/icon-256.png
    DESTINATION share/icons/hicolor/256x256/apps
    RENAME shadowcypher.png)
