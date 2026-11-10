#!/usr/bin/env python3
"""Public members of a platform type, by reflection over the assemblies of a local installation.

    python api.py Terrasoft.Core.DB.Select --bin <site>/Terrasoft.WebApp/bin
    python api.py Select Column                       # a short name; members whose name starts with "Column"
    python api.py EntitySchemaQuery AddColumn --bin <folder>   (or set CREATIO_BIN)

The folder is a site's `bin/` (.NET Framework) or `.application/net-framework/core-bin`. Windows PowerShell
loads each assembly reflection-only (nothing runs) and prints constructors, methods with their overloads and
parameter types, properties, fields and events. Exit 1 when no type matches; 2 on a usage error.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$global:apibin = $env:API_BIN; $want = $env:API_TYPE; $member = $env:API_MEMBER
[AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve([ResolveEventHandler]{ param($s, $e)
    $f = Join-Path $global:apibin ((New-Object Reflection.AssemblyName($e.Name)).Name + '.dll')
    if (Test-Path $f) { return [Reflection.Assembly]::ReflectionOnlyLoadFrom($f) }
    return [Reflection.Assembly]::ReflectionOnlyLoad($e.Name) })
$flags = [Reflection.BindingFlags]'Public,Instance,Static,DeclaredOnly'
function P($m) { ($m.GetParameters() | ForEach-Object { $_.ParameterType.Name + ' ' + $_.Name }) -join ', ' }
# a full name stops at the first assembly that has it, and that assembly is tried first (Terrasoft.Core.DB.Select -> Terrasoft.Core.dll)
$dlls = Get-ChildItem $global:apibin -Filter *.dll | Sort-Object { if ($want.StartsWith($_.BaseName + '.')) { -$_.BaseName.Length } else { 1 } }
foreach ($dll in $dlls) {
    try { $asm = [Reflection.Assembly]::ReflectionOnlyLoadFrom($dll.FullName) } catch { continue }
    try { $types = $asm.GetTypes() } catch [Reflection.ReflectionTypeLoadException] { $types = $_.Exception.Types } catch { $types = $_.Exception.InnerException.Types }
    $found = $false
    foreach ($t in $types) {
        if (-not $t -or -not $t.IsPublic -or ($t.FullName -ne $want -and $t.Name -ne $want)) { continue }
        $found = $true
        $base = ''; try { $base = [string]$t.BaseType.FullName } catch { }
        "TYPE`t$($t.FullName)`t$($dll.Name)`t$base"
        foreach ($m in $t.GetMembers($flags)) {
            if ($member -and -not $m.Name.StartsWith($member)) { continue }
            switch ($m.MemberType) {
                'Constructor' { "M`tctor`t$($t.Name)`t$(P $m)" }
                'Method' { if (-not $m.IsSpecialName) { $s = if ($m.IsStatic) { 'static ' } else { '' }; "M`tmethod`t$($m.Name)`t$s$($m.ReturnType.Name) ($(P $m))" } }
                'Property' { "M`tproperty`t$($m.Name)`t$($m.PropertyType.Name)" }
                'Field' { "M`tfield`t$($m.Name)`t$($m.FieldType.Name)" }
                'Event' { "M`tevent`t$($m.Name)`t$($m.EventHandlerType.Name)" }
            }
        }
    }
    if ($found -and $want.Contains('.')) { break }
}
"""


def run_powershell(bin_dir: str, type_name: str, member: str) -> str:
    env = {**os.environ, "API_BIN": bin_dir, "API_TYPE": type_name, "API_MEMBER": member}
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env, check=False)
    except OSError as e:
        raise RuntimeError(f"could not run Windows PowerShell: {e}") from e
    return r.stdout


def format_members(output: str) -> tuple[list[str], int]:
    """PowerShell's tab-separated lines -> the printed listing and the number of types found."""
    out, types = [], 0
    order = {"ctor": 0, "method": 1, "property": 2, "field": 3, "event": 4}
    members: list[tuple] = []

    def flush():
        for _, kind, name, sig in sorted(members, key=lambda m: (order[m[1]], m[2].lower(), m[3])):
            out.append(f"  {kind:<9}{name}({sig})" if kind == "ctor" else f"  {kind:<9}{name}  {sig}")
        members.clear()

    for line in output.splitlines():
        parts = line.rstrip("\r").split("\t")
        if parts[0] == "TYPE" and len(parts) >= 3:
            flush()
            types += 1
            out.append(f"{parts[1]}  ({parts[2]}" + (f"; base {parts[3]})" if len(parts) > 3 and parts[3] else ")"))
        elif parts[0] == "M" and len(parts) == 4:
            members.append(tuple(parts))
    flush()
    return out, types


def main(argv=None, runner=run_powershell) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("type", help="full name (Terrasoft.Core.DB.Select) or short name (Select)")
    p.add_argument("member", nargs="?", default="", help="only members whose name starts with this")
    p.add_argument("--bin", default=os.environ.get("CREATIO_BIN"), help="the assemblies folder; default $CREATIO_BIN")
    a = p.parse_args(argv)
    if not a.bin or not Path(a.bin).is_dir():
        print(f"error: --bin must name an assemblies folder (got {a.bin!r}); or set CREATIO_BIN", file=sys.stderr)
        return 2
    try:
        lines, types = format_members(runner(str(Path(a.bin).resolve()), a.type, a.member))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not types:
        print(f"no public type {a.type!r} in {a.bin}")
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
