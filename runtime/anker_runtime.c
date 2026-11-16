/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Thin adapter around the Wine host ABI from the upstream source tree.
 * This is built ONLY when native dependencies and wine_host.h are staged.
 * Never compile a fake implementation that reports a successful launch.
 */
#include "anker_runtime.h"
#include "wine_host.h"
#include <string.h>
#include <limits.h>

int anker_runtime_abi_version(void) { return ANKER_RUNTIME_ABI_VERSION; }

int anker_runtime_initialize(const anker_runtime_config *cfg) {
    if (!cfg || !cfg->runtime_directory || !cfg->prefix_directory ||
        !cfg->log_path || !cfg->jit_rx || !cfg->jit_rw || !cfg->jit_size) return -1;
    if (wine_host_abi_version() != WINE_HOST_ABI_VERSION) return -2;
    wine_host_config host;
    memset(&host, 0, sizeof(host));
    host.abi_version = WINE_HOST_ABI_VERSION;
    host.runtime_dir = cfg->runtime_directory;
    host.prefix_dir = cfg->prefix_directory;
    host.log_path = cfg->log_path;
    host.jit_rx = cfg->jit_rx;
    host.jit_rw = cfg->jit_rw;
    host.jit_size = cfg->jit_size;
    return wine_host_init(&host);
}
int anker_runtime_start_session(int timeout_ms) {
    return wine_host_session_start(timeout_ms);
}
int anker_runtime_launch(const char *path, const char *const *args, int nargs,
                         const char *const *env, int nenv, int timeout_ms) {
    if (!path || !path[0] || nargs < 0 || nenv < 0) return -1;
    return wine_host_session_launch(path, args, nargs, env, nenv, timeout_ms);
}
int anker_runtime_wait(int timeout_ms, int *exit_code) {
    return wine_host_session_wait(timeout_ms, exit_code);
}
