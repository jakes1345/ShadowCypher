cmake_minimum_required(VERSION 3.21)
project(ShadowCypher VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

find_package(Qt6 REQUIRED COMPONENTS
    Core
    Gui
    Quick
    QuickControls2
    Network
    Concurrent
    WebSockets
)

qt_standard_project_setup()

set(SOURCES
    src/main.cpp
    src/App.cpp
    src/core/Config.cpp
    src/core/ApiClient.cpp
    src/scanner/NetworkScanner.cpp
    src/scanner/ArpMonitor.cpp
    src/ai/OllamaClient.cpp
    src/privacy/PrivacyMode.cpp
)

set(HEADERS
    src/App.h
    src/core/Config.h
    src/core/ApiClient.h
    src/scanner/NetworkScanner.h
    src/scanner/ArpMonitor.h
    src/ai/OllamaClient.h
    src/privacy/PrivacyMode.h
)

qt_add_executable(shadowcypher ${SOURCES} ${HEADERS})

qt_add_qml_module(shadowcypher
    URI ShadowCypher
    VERSION 1.0
    QML_FILES
        src/ui/qml/Main.qml
        src/ui/qml/Sidebar.qml
        src/ui/qml/DashboardPage.qml
        src/ui/qml/NetworkPage.qml
        src/ui/qml/AIPage.qml
        src/ui/qml/PrivacyPage.qml
        src/ui/qml/SettingsPage.qml
        src/ui/qml/Components.qml
)

target_include_directories(shadowcypher PRIVATE src)

target_link_libraries(shadowcypher PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::Network
    Qt6::Concurrent
    Qt6::WebSockets
)

# Platform-specific
if(WIN32)
    target_compile_definitions(shadowcypher PRIVATE SC_WINDOWS)
    target_link_libraries(shadowcypher PRIVATE iphlpapi ws2_32)
    set_target_properties(shadowcypher PROPERTIES WIN32_EXECUTABLE TRUE)
elseif(UNIX)
    target_compile_definitions(shadowcypher PRIVATE SC_LINUX)
endif()

# App metadata
set_target_properties(shadowcypher PROPERTIES
    OUTPUT_NAME "shadowcypher"
    MACOSX_BUNDLE_GUI_IDENTIFIER "site.shadowcypher.desktop"
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
)

install(TARGETS shadowcypher
    BUNDLE  DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
