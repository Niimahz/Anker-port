/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef ANKER_RUNTIME_H
#define ANKER_RUNTIME_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#define ANKER_RUNTIME_ABI_VERSION 1
typedef struct {
    const char *runtime_directory;
    const char *prefix_directory;
    const char *log_path;
    void *jit_rx;
    void *jit_rw;
    size_t jit_size;
} anker_runtime_config;
int anker_runtime_abi_version(void);
int anker_runtime_initialize(const anker_runtime_config *config);
int anker_runtime_start_session(int timeout_ms);
int anker_runtime_launch(const char *dos_path, const char *const *args, int nargs,
                         const char *const *env, int nenv, int timeout_ms);
int anker_runtime_wait(int timeout_ms, int *exit_code);
#ifdef __cplusplus
}
#endif
#endif
