cmake_minimum_required(VERSION 3.16)

find_package(Qt6 REQUIRED COMPONENTS Core Network Concurrent)

add_executable(shadowcypher-daemon
    main.cpp
    Daemon.cpp
    Daemon.h
)

target_include_directories(shadowcypher-daemon PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(shadowcypher-daemon PRIVATE
    shadow_runtime
    Qt6::Core
    Qt6::Network
    Qt6::Concurrent
)

if(NOT MSVC)
    target_compile_options(shadowcypher-daemon PRIVATE -Wall -Wextra -O2)
else()
    target_compile_options(shadowcypher-daemon PRIVATE /W3 /O2)
endif()

install(TARGETS shadowcypher-daemon RUNTIME DESTINATION bin)
