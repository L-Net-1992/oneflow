set(BUILD_CUDA YES CACHE BOOL "")
set(BUILD_GIT_VERSION YES CACHE BOOL "")
set(BUILD_TESTING OFF CACHE BOOL "")
set(BUILD_RDMA YES CACHE BOOL "")
set(TREAT_WARNINGS_AS_ERRORS YES CACHE BOOL "")
set(THIRD_PARTY_MIRROR aliyun CACHE STRING "")
set(PIP_INDEX_MIRROR "https://pypi.tuna.tsinghua.edu.cn/simple" CACHE STRING "")
set(CMAKE_BUILD_TYPE Release CACHE STRING "")
set(CMAKE_GENERATOR Ninja CACHE STRING "")
set(CUDNN_STATIC OFF CACHE BOOL "")
set(WITH_MLIR ON CACHE BOOL "")
set(BUILD_CPP_API OFF CACHE BOOL "")
set(CUDA_NVCC_THREADS_NUMBER 2 CACHE STRING "")
set(CMAKE_C_COMPILER_LAUNCHER ccache CACHE STRING "")
set(CMAKE_CXX_COMPILER_LAUNCHER ccache CACHE STRING "")
set(CMAKE_CUDA_COMPILER_LAUNCHER ccache CACHE STRING "")
set(CMAKE_CXX_FLAGS
    "-Wno-unused-but-set-parameter -Wno-unused-variable -Wno-class-memaccess -Wno-cast-function-type -Wno-comment -Wno-reorder"
    CACHE STRING "")
