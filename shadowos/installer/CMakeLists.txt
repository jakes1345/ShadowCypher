cmake_minimum_required(VERSION 3.16)
project(shadowos-installer VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets)

qt_add_executable(shadowos-installer
    src/main.cpp
    src/Installer.cpp
    src/Installer.h
    src/theme.h
    src/InstallState.h
    src/DiskUtil.cpp
    src/DiskUtil.h
    src/pages/WelcomePage.cpp
    src/pages/WelcomePage.h
    src/pages/DiskPage.cpp
    src/pages/DiskPage.h
    src/pages/EncryptPage.cpp
    src/pages/EncryptPage.h
    src/pages/UserPage.cpp
    src/pages/UserPage.h
    src/pages/ProfilePage.cpp
    src/pages/ProfilePage.h
    src/pages/SummaryPage.cpp
    src/pages/SummaryPage.h
    src/pages/InstallPage.cpp
    src/pages/InstallPage.h
    src/pages/FinishPage.cpp
    src/pages/FinishPage.h
)

target_link_libraries(shadowos-installer PRIVATE
    Qt6::Core
    Qt6::Widgets
)

target_compile_options(shadowos-installer PRIVATE -Wall -Wextra -O2)

install(TARGETS shadowos-installer DESTINATION usr/local/bin)
install(FILES shadowos-installer.desktop DESTINATION usr/share/applications)
