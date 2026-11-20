#pragma once
#include "archive.h"
#include "archive_entry.h"
#include <fts.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <limits.h>
#include <errno.h>

// Copy the pristine runtime and stream the selected game's tree to one ZIP64-capable writer.
static inline int port_build_ipa(const char *seed, const char *prefix, const char *game,
                                 const char *plist, const char *profile, const char *output,
                                 char *error, size_t capacity) {
    struct archive *r = archive_read_new(), *w = archive_write_new();
    struct archive_entry *item = NULL;
    FTS *tree = NULL;
    FILE *file = NULL;
    int result = -1, rc;
    const char *reason = NULL;
    char buffer[65536], name[PATH_MAX];
    if (!r || !w) { reason = "Out of memory"; goto done; }
    archive_read_support_format_zip(r);
    if (archive_read_open_filename(r, seed, sizeof(buffer)) != ARCHIVE_OK) goto done;
    if (archive_write_set_format_zip(w) != ARCHIVE_OK ||
        archive_write_set_format_option(w, "zip", "compression", "store") != ARCHIVE_OK ||
        archive_write_open_filename(w, output) != ARCHIVE_OK) goto done;
    struct archive_entry *entry;
    while ((rc = archive_read_next_header(r, &entry)) == ARCHIVE_OK) {
        const char *path = archive_entry_pathname(entry);
        if (!path || strncmp(path, prefix, strlen(prefix))) continue;
        const char *rel = path + strlen(prefix);
        if (!strcmp(rel,"Info.plist") || !strncmp(rel,"_CodeSignature/",15) ||
            !strcmp(rel,"embedded.mobileprovision")) continue;
        if (archive_write_header(w, entry) != ARCHIVE_OK) goto done;
        la_ssize_t n;
        while ((n = archive_read_data(r, buffer, sizeof(buffer))) > 0)
            if (archive_write_data(w, buffer, n) != n) goto done;
        if (n < 0 || archive_write_finish_entry(w) != ARCHIVE_OK) goto done;
    }
    if (rc != ARCHIVE_EOF) goto done;
    char *roots[] = {(char *)game, NULL};
    tree = fts_open(roots, FTS_PHYSICAL | FTS_NOCHDIR, NULL);
    if (!tree) { reason = strerror(errno); goto done; }
    int index = 0;
    for (;;) {
        const char *source;
        int directory = 0;
        if (index < 2) {
            source = index == 0 ? plist : profile;
            snprintf(name, sizeof(name), "%s%s", prefix, index == 0 ? "Info.plist" : "PortGame.json");
            index++;
        } else {
            errno = 0;
            FTSENT *node = fts_read(tree);
            if (!node) { if (errno) { reason = strerror(errno); goto done; } break; }
            if (node->fts_info == FTS_DP) continue;
            if (node->fts_info != FTS_D && node->fts_info != FTS_F) { reason = "Unreadable file or unsupported link in game folder"; goto done; }
            directory = node->fts_info == FTS_D;
            source = node->fts_path;
            if (snprintf(name,sizeof(name),"%sPortGameFiles%s",prefix,source + strlen(game)) >= (int)sizeof(name)) {
                reason = "Game path too long"; goto done;
            }
        }
        struct stat st;
        if (lstat(source, &st)) { reason = strerror(errno); goto done; }
        item = archive_entry_new();
        if (!item) { reason = "Out of memory"; goto done; }
        archive_entry_set_pathname(item, name);
        archive_entry_set_filetype(item, directory ? AE_IFDIR : AE_IFREG);
        archive_entry_set_perm(item, directory ? 0755 : 0644);
        archive_entry_set_size(item, directory ? 0 : st.st_size);
        if (archive_write_header(w,item) != ARCHIVE_OK) goto done;
        if (!directory) {
            file = fopen(source,"rb");
            if (!file) { reason = strerror(errno); goto done; }
            size_t n; off_t total = 0;
            while ((n = fread(buffer,1,sizeof(buffer),file)) > 0) {
                if (archive_write_data(w,buffer,n) != (la_ssize_t)n) goto done;
                total += n;
            }
            if (ferror(file) || total != st.st_size) { reason = "Game file changed or could not be read"; goto done; }
            fclose(file); file = NULL;
        }
        if (archive_write_finish_entry(w) != ARCHIVE_OK) goto done;
        archive_entry_free(item); item = NULL;

    }
    if (archive_write_close(w) != ARCHIVE_OK) goto done;
    result = 0;
done:
    if (result) {
        if (!reason && w) reason = archive_error_string(w);
        if (!reason && r) reason = archive_error_string(r);
        snprintf(error,capacity,"%s",reason ? reason : "Could not create IPA");
    }
    if (file) fclose(file);
    if (tree) fts_close(tree);
    if (item) archive_entry_free(item);
    if (w) archive_write_free(w);
    if (r) archive_read_free(r);
    return result;
}
