#include <ntddk.h>

/* smoke.c - minimal hello-world kernel driver for the Tier-1 kernel lab.
 *
 * Lifecycle:
 *   load   : sc create smoke type= kernel binPath= <path>\smoke.sys
 *            sc start smoke
 *   observe: DbgPrint output streams to the attached WinDbg session.
 *   unload : sc stop smoke   (DO NOT delete the service while testing;
 *            reuse it for the next build via sc stop/start)
 *
 * No device, no IOCTL - this file proves the build -> drop -> load ->
 * debug loop end to end. The read primitive is the next iteration.
 */

VOID
SmokeUnload(
    _In_ PDRIVER_OBJECT DriverObject
)
{
    UNREFERENCED_PARAMETER(DriverObject);
    DbgPrint("[smoke] unloading\n");
}

NTSTATUS
DriverEntry(
    _In_ PDRIVER_OBJECT  DriverObject,
    _In_ PUNICODE_STRING RegistryPath
)
{
    UNREFERENCED_PARAMETER(RegistryPath);

    DbgPrint("[smoke] hello from ring 0 (build tag: smoke-1)\n");
    DriverObject->DriverUnload = SmokeUnload;

    return STATUS_SUCCESS;
}
