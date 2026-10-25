<#
Open the OpenPLC web UIs, which Docker cannot publish (ADR-013, ADR-014).

    powershell -ExecutionPolicy Bypass -File tools\plc-ui-relay.ps1 -Action start -Target control
    powershell -ExecutionPolicy Bypass -File tools\plc-ui-relay.ps1 -Action start -Target safety -ConfirmSafety
    powershell -ExecutionPolicy Bypass -File tools\plc-ui-relay.ps1 -Action stop
    powershell -ExecutionPolicy Bypass -File tools\plc-ui-relay.ps1 -Action status

WHY IT EXISTS
  net_control and net_safety are `internal: true`, and Docker ignores `ports:` on
  an internal network. The compose file's 8081 and 8082 mappings therefore do
  nothing, and nobody can load a program. The honest fix is not to un-internal
  the network, so a throwaway socat container is attached to the internal network
  for as long as you need the UI, published on loopback, and then removed.

  control -> http://127.0.0.1:8081   (login openplc / openplc)
  safety  -> http://localhost:8082   (a DIFFERENT host name on purpose: browsers
             share cookies across ports on one host, and the two UIs overwrite
             each other's session)

THE SAFETY RELAY IS A SECOND MEMBER OF net_safety while it runs. ADR-014 allows
that as a deliberate, temporary, human act, and prove-isolation.ps1 fails if one
is left behind. Hence -ConfirmSafety, and hence `-Action stop` at the end.
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('start', 'stop', 'status')][string]$Action,
    [ValidateSet('control', 'safety')][string]$Target = 'control',
    [switch]$ConfirmSafety
)
$ErrorActionPreference = 'Continue'   # native stderr must not become a terminating error in Windows PowerShell 5.1

$cfg = @{
    control = @{ name = 'vigilimen-relay-control'; net = 'vigilimen-plant_net_control'; svc = 'plc-control'; port = 8081 }
    safety  = @{ name = 'vigilimen-relay-safety';  net = 'vigilimen-plant_net_safety';  svc = 'plc-safety';  port = 8082 }
}

switch ($Action) {
    'start' {
        $c = $cfg[$Target]
        if ($Target -eq 'safety' -and -not $ConfirmSafety) {
            Write-Host "This puts a SECOND container on net_safety until you run -Action stop."
            Write-Host "Re-run with -ConfirmSafety if you mean it."
            exit 1
        }
        docker rm -f $c.name 2>$null | Out-Null
        # Created on the default bridge (so the port can be published), THEN attached to the internal network.
        docker run -d --rm --name $c.name -p "127.0.0.1:$($c.port):8080" alpine/socat "tcp-listen:8080,fork,reuseaddr" "tcp:$($c.svc):8080" | Out-Null
        docker network connect $c.net $c.name
        Write-Host "relay up: http://127.0.0.1:$($c.port)  ->  $($c.svc):8080"
        if ($Target -eq 'safety') { Write-Host "Use http://localhost:8082 if the control UI is open on 127.0.0.1 (cookies)." }
    }
    'stop' {
        foreach ($k in $cfg.Keys) { docker rm -f $cfg[$k].name 2>$null | Out-Null }
        Write-Host "relays removed"
    }
    'status' {
        docker ps --filter "name=vigilimen-relay" --format "{{.Names}}  {{.Ports}}"
    }
}
