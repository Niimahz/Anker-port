#import <Foundation/Foundation.h>
#include <SDL.h>

extern int boxedmain(int, const char**);
extern "C" void MacPlatformOpenFileLocation(const char*) {}
extern "C" const char* MacPlatformGetResourcePath(const char*) { return nullptr; }

int SDL_main(int, char**) {
    @autoreleasepool {
        NSBundle *bundle = NSBundle.mainBundle;
        NSString *relative = [bundle objectForInfoDictionaryKey:@"AnkerNativeExecutable"];
        NSURL *assets = [bundle.bundleURL URLByAppendingPathComponent:@"PortGameFiles"];
        if (!relative.length || relative.isAbsolutePath || [relative.pathComponents containsObject:@".."]) return 1;
        NSFileManager *fm = NSFileManager.defaultManager;
        NSURL *support = [fm URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask].firstObject;
        NSURL *root = [support URLByAppendingPathComponent:@"Wine"];
        NSURL *game = [support URLByAppendingPathComponent:@"Game"];
        NSError *error = nil;
        if (![fm createDirectoryAtURL:root withIntermediateDirectories:YES attributes:nil error:&error]) {
            NSLog(@"Wine directory: %@", error); return 1;
        }
        if (![fm fileExistsAtPath:game.path]) {
            NSURL *stage = [support URLByAppendingPathComponent:NSUUID.UUID.UUIDString];
            if (![fm copyItemAtURL:assets toURL:stage error:&error] || ![fm moveItemAtURL:stage toURL:game error:&error]) {
                [fm removeItemAtURL:stage error:nil]; NSLog(@"Game install: %@", error); return 1;
            }
        }
        if (![fm fileExistsAtPath:[game URLByAppendingPathComponent:relative].path]) return 1;
        NSString *cwd = [@"/home/username/.wine/dosdevices/d:" stringByAppendingPathComponent:relative.stringByDeletingLastPathComponent];
        NSURL *wine = [bundle.bundleURL URLByAppendingPathComponent:@"wine.zip"];
        const char *args[] = {"Anker", "-root", root.fileSystemRepresentation, "-zip", wine.fileSystemRepresentation,
            "-mount_drive", game.fileSystemRepresentation, "d", "-w", cwd.UTF8String, "/bin/wine", relative.lastPathComponent.UTF8String};
        return boxedmain(sizeof(args)/sizeof(args[0]), args);
    }
}
