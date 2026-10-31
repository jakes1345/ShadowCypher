cmake_minimum_required(VERSION 3.16)
project(ShadowCypherRuntime VERSION 0.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 6.4 REQUIRED COMPONENTS Core Network)

add_library(shadow_runtime STATIC
    Process.cpp Process.h
    ShadowScript.cpp ShadowScript.h
    NativeTools.cpp NativeTools.h
    Protocol.cpp Protocol.h
    MissionRunner.cpp MissionRunner.h)
target_include_directories(shadow_runtime PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(shadow_runtime PUBLIC Qt6::Core Qt6::Network)
target_compile_options(shadow_runtime PRIVATE $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall;-Wextra;-Wpedantic>)
add_executable(shadowcypher-runtime main.cpp)
target_link_libraries(shadowcypher-runtime PRIVATE shadow_runtime)
install(TARGETS shadowcypher-runtime RUNTIME DESTINATION bin)

include(CTest)
if(BUILD_TESTING)
    find_package(Qt6 REQUIRED COMPONENTS Test)
    add_executable(runtime_tests tests/RuntimeTests.cpp)
    target_link_libraries(runtime_tests PRIVATE shadow_runtime Qt6::Test)
    target_compile_definitions(runtime_tests PRIVATE SHADOW_RUNTIME_PATH="$<TARGET_FILE:shadowcypher-runtime>")
    target_compile_definitions(runtime_tests PRIVATE SHADOW_SCRIPT_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../../shadowscript")
    add_dependencies(runtime_tests shadowcypher-runtime)
    add_test(NAME runtime_tests COMMAND runtime_tests)
endif()
