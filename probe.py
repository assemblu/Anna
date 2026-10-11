Import argparse
import ctypes
import ctypes.wintypes as w
import sys

ARCHIVE_CLIENT_DLL = r"research/artifacts/2026-10-11_buildid-25815307/bin/client.dll"

def archive_image_size():
    import struct
    with open(ARCHIVE_CLIENT_DLL, "rb") as f:
        d = f.read(0x400)
    e = struct.unpack_from("<I", d, 0x3C)[0]
    opt = e + 0x18
    assert struct.unpack_from("<H", d, opt)[0] == 0x20B
    return struct.unpack_from("<I", d, opt + 0x38)[0]
ANCHORS = {
    0x2793AA0: "g_schema_system_ptr",
    0x2557BA8: "g_iface_req",
}

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400


def find_process_module(pname: str, mname: str):
    """Return (pid, modbase, modsize) for the first process `pname` containing module `mname`."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    class MODULEINFO(ctypes.Structure):
        _fields_ = [("lpBaseOfDll", w.LPVOID), ("SizeOfImage", w.DWORD), ("EntryPoint", w.LPVOID)]

    kernel32.K32EnumProcesses.restype = w.BOOL
    kernel32.K32EnumProcesses.argtypes = [ctypes.POINTER(w.DWORD), w.DWORD, ctypes.POINTER(w.DWORD)]
    kernel32.OpenProcess.restype = w.HANDLE
    kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel32.K32GetProcessImageFileNameW.restype = w.DWORD
    kernel32.K32GetProcessImageFileNameW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD]
    kernel32.CloseHandle.argtypes = [w.HANDLE]
    psapi.EnumProcessModulesEx.restype = w.BOOL
    psapi.EnumProcessModulesEx.argtypes = [w.HANDLE, ctypes.POINTER(w.HMODULE), w.DWORD, ctypes.POINTER(w.DWORD), w.DWORD]
    psapi.GetModuleBaseNameW.restype = w.DWORD
    psapi.GetModuleBaseNameW.argtypes = [w.HANDLE, w.HMODULE, w.LPWSTR, w.DWORD]
    psapi.GetModuleInformation.restype = w.BOOL
    psapi.GetModuleInformation.argtypes = [w.HANDLE, w.HMODULE, ctypes.POINTER(MODULEINFO), w.DWORD]

    PIDs = (w.DWORD * 1024)()
    cb = w.DWORD()
    kernel32.K32EnumProcesses(PIDs, ctypes.sizeof(PIDs), ctypes.byref(cb))
    n = cb.value // ctypes.sizeof(w.DWORD)
    for i in range(n):
        pid = PIDs[i]
        h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not h:
            continue
        try:
            name = ctypes.create_unicode_buffer(260)
            kernel32.K32GetProcessImageFileNameW(h, name, 260)
            base = name.value.rsplit("\\", 1)[-1].lower()
            if base != pname.lower():
                continue
            hmods = (w.HMODULE * 1024)(), w.DWORD()
            if not psapi.EnumProcessModulesEx(h, hmods[0], ctypes.sizeof(hmods[0]), ctypes.byref(hmods[1]), 3):
                continue
            for j in range(hmods[1].value // ctypes.sizeof(w.HMODULE)):
                mb = ctypes.create_unicode_buffer(260)
                if not psapi.GetModuleBaseNameW(h, hmods[0][j], mb, 260):
                    continue
                if mb.value.lower() == mname.lower():
                    mi = MODULEINFO()
                    if psapi.GetModuleInformation(h, hmods[0][j], ctypes.byref(mi), ctypes.sizeof(mi)):
                        return pid, mi.lpBaseOfDll, mi.SizeOfImage
        finally:
            kernel32.CloseHandle(h)
    return None


def read_qword(h, addr):
    v = ctypes.c_ulonglong()
    n = ctypes.c_size_t()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.ReadProcessMemory.restype = w.BOOL
    kernel32.ReadProcessMemory.argtypes = [w.HANDLE, w.LPCVOID, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    if not kernel32.ReadProcessMemory(h, ctypes.c_void_p(addr), ctypes.byref(v), 8, ctypes.byref(n)):
        return None
    return v.value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rva", type=lambda x: int(x, 0), default=None)
    ap.add_argument("--rva-list", type=lambda x: int(x, 0), nargs="*", default=None)
    a = ap.parse_args()

    hit = find_process_module("cs2.exe", "client.dll")
    if not hit:
        print("NOT RUNNING: cs2.exe with client.dll not found")
        sys.exit(1)
    pid, base, size = hit
    print(f"cs2.exe pid={pid}")
    print(f"client.dll base={base:#x} live SizeOfImage={size}")
    arch = archive_image_size()
    print(f"archive SizeOfImage={arch}")
    if size != arch:
        print("!! IMAGE MISMATCH -> game updated; re-capture + re-derive before trusting RVAs")
        sys.exit(2)
    print("build-match: OK (live image == archive image)")

    if a.rva is not None:
        a.rva_list = [a.rva] if a.rva_list is None else a.rva_list
    targets = a.rva_list or list(ANCHORS.keys())
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        print("OpenProcess failed", ctypes.get_last_error())
        sys.exit(1)
    try:
        for rva in targets:
            v = read_qword(h, base + rva)
            name = ANCHORS.get(rva, f"rva {rva:#x}")
            vt = None
            if v:
                vt = read_qword(h, v)
            print(f"{name} @ client.dll+{rva:#x} = {v and hex(v)} vtable_first={vt and hex(vt)}")
    finally:
        kernel32.CloseHandle(h)


if __name__ == "__main__":
    main()
