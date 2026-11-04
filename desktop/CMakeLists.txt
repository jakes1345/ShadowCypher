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
)

qt_standard_project_setup()

set(SOURCES
    src/main.cpp
    src/App.cpp
    src/core/Config.cpp
    src/core/ApiClient.cpp
    src/core/CloudData.cpp
    src/scanner/NetworkScanner.cpp
    src/scanner/ArpMonitor.cpp
    src/ai/OllamaClient.cpp
    src/privacy/PrivacyMode.cpp
)

set(HEADERS
    src/App.h
    src/core/Config.h
    src/core/ApiClient.h
    src/core/CloudData.h
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
        src/ui/qml/NavItem.qml
        src/ui/qml/StatTile.qml
        src/ui/qml/Toast.qml
        src/ui/qml/DashboardPage.qml
        src/ui/qml/NetworkPage.qml
        src/ui/qml/AIPage.qml
        src/ui/qml/PrivacyPage.qml
        src/ui/qml/SettingsPage.qml
)

target_include_directories(shadowcypher PRIVATE src)

target_link_libraries(shadowcypher PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::Network
)

# Platform-specific
if(WIN32)
    target_compile_definitions(shadowcypher PRIVATE SC_WINDOWS)
    target_link_libraries(shadowcypher PRIVATE iphlpapi ws2_32)
    set_target_properties(shadowcypher PROPERTIES WIN32_EXECUTABLE TRUE)
elseif(UNIX)
    target_compile_definitions(shadowcypher PRIVATE SC_LINUX)

    # Root helper for privacy mode, run through pkexec. Kept free of Qt so the
    # code that runs privileged stays small.
    add_executable(shadowcypher-privacy-helper src/privacy/helper/main.cpp)
    target_compile_options(shadowcypher-privacy-helper PRIVATE -Wall -Wextra)
    # Runs as root: no $ORIGIN-relative library search path.
    set_target_properties(shadowcypher-privacy-helper PROPERTIES INSTALL_RPATH "")

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
