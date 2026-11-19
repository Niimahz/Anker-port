#pragma once
#include "archive.h"
#include "archive_entry.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>

// The caller owns a freshly created private staging directory.
static inline int anker_unpack(const char *input, const char *root, char *error, size_t capacity) {
    struct archive *reader = archive_read_new();
    if (!reader) { snprintf(error, capacity, "Out of memory"); return -1; }
    archive_read_support_format_zip(reader);
    archive_read_support_format_rar(reader);
    archive_read_support_format_rar5(reader);
    archive_read_support_format_7zip(reader);
    const char *reason = NULL;
    int fd = -1, count = 0;
    if (archive_read_open_filename(reader, input, 65536) != ARCHIVE_OK) goto fail;
    struct archive_entry *entry;
    int rc;
    while ((rc = archive_read_next_header(reader, &entry)) == ARCHIVE_OK) {
        const char *name = archive_entry_pathname_utf8(entry);
        if (!name) name = archive_entry_pathname(entry);
        mode_t type = archive_entry_filetype(entry);
        if (!name || !*name || *name == '/' || *name == '\\' || strchr(name, ':') ||
            archive_entry_hardlink(entry) || archive_entry_symlink(entry) ||
            (type != AE_IFDIR && type != AE_IFREG)) {
            reason = "Unsupported path or link in archive"; goto fail;
        }
        char path[PATH_MAX];
        if (snprintf(path, sizeof(path), "%s/%s", root, name) >= (int)sizeof(path)) {
            reason = "File path is too long"; goto fail;
        }
        char *part = path + strlen(root) + 1;
        for (char *p = part; ; ++p) {
            if (*p != '/' && *p != '\\' && *p != '\0') continue;
            int last = !*p;
            *p = '\0';
            if (!strcmp(part, "..")) { reason = "Archive contains a parent path"; goto fail; }
            if (*part && strcmp(part, ".") && (!last || type == AE_IFDIR)) {
                if (mkdir(path, 0700) && errno != EEXIST) { reason = strerror(errno); goto fail; }
                struct stat st;
                if (lstat(path, &st) || !S_ISDIR(st.st_mode)) { reason = "Folder name conflict"; goto fail; }
            }
            if (last) break;
            *p = '/'; part = p + 1;
        }
        if (type == AE_IFDIR) continue;
        fd = open(path, O_CREAT | O_EXCL | O_NOFOLLOW | O_WRONLY, 0600);
        if (fd < 0) { reason = strerror(errno); goto fail; }
        if (archive_read_data_into_fd(reader, fd) != ARCHIVE_OK) goto fail;
        int closed = close(fd);
        fd = -1;
        if (closed) { reason = strerror(errno); goto fail; }
        ++count;
    }
    if (rc != ARCHIVE_EOF) goto fail;
    if (archive_read_close(reader) != ARCHIVE_OK) goto fail;
    if (!count) { reason = "Archive contains no files"; goto fail; }
    archive_read_free(reader);
    return 0;
fail:
    if (!reason) reason = archive_error_string(reader);
    snprintf(error, capacity, "%s", reason ? reason : "Unreadable or incomplete archive");
    if (fd >= 0) close(fd);
    archive_read_free(reader);
    return -1;
}
