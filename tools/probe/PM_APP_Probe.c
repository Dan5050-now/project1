/* PM_APP launch probe - the smallest honest test of A-N09.
 *
 * The full desktop package is 142 MB and cannot be delivered down a channel with a
 * 30 MiB limit. But the question it was meant to answer is not about size:
 *
 *     will this machine let its user extract a zip into a folder of their own
 *     and RUN AN UNSIGNED EXECUTABLE from it?
 *
 * Application allow-listing, SmartScreen and Mark-of-the-Web all judge a file by its
 * signature, its origin and its reputation - not by how many megabytes it is. So a
 * 60 KB unsigned executable, arriving by the same route and run from the same place,
 * meets the same policies as the real one would.
 *
 * What it does NOT test is anti-virus behaviour towards a 344 MB Chromium application,
 * and how long that takes to start from a network folder. Those need the real package,
 * and this program says so on screen rather than letting anybody think otherwise.
 *
 * It writes its findings to a file beside itself, so the result can be sent back
 * rather than remembered.
 *
 *   x86_64-w64-mingw32-gcc -O2 -mwindows -o PM_APP_Probe.exe PM_APP_Probe.c
 */

#include <windows.h>
#include <stdio.h>

static void line(char *buf, size_t cap, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    size_t used = strlen(buf);
    vsnprintf(buf + used, cap - used, fmt, ap);
    va_end(ap);
}

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show) {
    (void)inst; (void)prev; (void)cmd; (void)show;

    char report[4096] = {0};
    char exePath[MAX_PATH] = {0};
    char folder[MAX_PATH] = {0};
    char user[256] = {0};
    char host[256] = {0};
    DWORD n;

    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    strncpy(folder, exePath, MAX_PATH - 1);
    char *slash = strrchr(folder, '\\');
    if (slash) *slash = '\0';

    n = sizeof(user);  GetUserNameA(user, &n);
    n = sizeof(host);  GetComputerNameA(host, &n);

    SYSTEMTIME st;
    GetLocalTime(&st);

    line(report, sizeof report,
         "PM_APP launch probe - result\r\n"
         "============================\r\n\r\n"
         "IT RAN. That is the main finding: this machine allowed an unsigned\r\n"
         "executable, extracted from a zip into a user folder, to start.\r\n\r\n"
         "When   %04d-%02d-%02d %02d:%02d\r\n"
         "Who    %s\r\n"
         "Where  %s\r\n"
         "Folder %s\r\n",
         st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, user, host, folder);

    /* Can it write beside itself? This is NR-DEP-09 and rule 3 of the data-folder
       order: if the answer is no, the real application must ask the user where to
       keep data instead of failing at the first Save. */
    char probeFile[MAX_PATH];
    snprintf(probeFile, sizeof probeFile, "%s\\PM_APP_probe_result.txt", folder);

    HANDLE h = CreateFileA(probeFile, GENERIC_WRITE, 0, NULL,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    BOOL canWrite = (h != INVALID_HANDLE_VALUE);

    line(report, sizeof report,
         "Write to its own folder   %s\r\n\r\n",
         canWrite ? "YES - the application would keep its data here"
                  : "NO - the application would have to ask you where to put data");

    line(report, sizeof report,
         "WHAT THIS DOES NOT TELL US\r\n"
         "  Whether anti-virus tolerates the real package, which is 344 MB and\r\n"
         "  carries a browser engine, and how long that takes to start. Those need\r\n"
         "  the full build.\r\n\r\n"
         "PLEASE ALSO SAY\r\n"
         "  * Did Windows show a blue 'Windows protected your PC' box first?\r\n"
         "  * Did you have to click 'More info' then 'Run anyway'?\r\n"
         "  * Did anything else appear - anti-virus, a policy message, a block?\r\n"
         "  * Did the zip extract without complaint?\r\n\r\n"
         "Send this file back, with those four answers.\r\n");

    if (canWrite) {
        DWORD written;
        WriteFile(h, report, (DWORD)strlen(report), &written, NULL);
        CloseHandle(h);
    }

    char msg[5120];
    snprintf(msg, sizeof msg,
             "%s\r\n%s",
             report,
             canWrite ? "This text has been saved as PM_APP_probe_result.txt in the same\r\n"
                        "folder. Please send that file back."
                      : "This folder is read-only, so nothing could be saved. Please copy\r\n"
                        "this text, or send a screenshot.");

    MessageBoxA(NULL, msg, "Project Management APP - launch probe",
                MB_OK | (canWrite ? MB_ICONINFORMATION : MB_ICONWARNING));
    return 0;
}
