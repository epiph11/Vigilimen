<#
Open the supervisory zone to the host: FUXA, the historian database and the read-only OPC UA server.

    powershell -ExecutionPolicy Bypass -File tools\supervisory-relay.ps1 -Action start -Target scada
    powershell -ExecutionPolicy Bypass -File tools\supervisory-relay.ps1 -Action start -Target historian
    powershell -ExecutionPolicy Bypass -File tools\supervisory-relay.ps1 -Action start -Target opcua
    powershell -ExecutionPolicy Bypass -File tools\supervisory-relay.ps1 -Action stop
    powershell -ExecutionPolicy Bypass -File tools\supervisory-relay.ps1 -Action status

WHY IT EXISTS
  Since ADR-023 / ADR-020 Q1 = a, net_supervisory is `internal: true`, and Docker ignores `ports:` on an
  internal network (see plc-ui-relay.ps1). The compose mappings for FUXA (1881) and the historian
  (15432) therefore do nothing. A throwaway socat container is created on the default bridge, so the port
  can be published on LOOPBACK ONLY, and then attached to net_supervisory. Remove it with -Action stop.

  scada      -> http://127.0.0.1:1881          FUXA
  historian  -> 127.0.0.1:15432                PostgreSQL (psql, a viewer)
  opcua      -> opc.tcp://127.0.0.1:14840/vigilimen/conv001/   opcua-sup: READ-ONLY, no command node

  There is deliberately NO relay to the gateway: it is not on net_supervisory, and the host has no
  business reaching the cell. To exercise the gateway, `docker exec` into the gateway container.

NOT VERIFIED when written (15 Nov 2026): this script has not been run. The pattern is the one plc-ui-relay.ps1
uses and that has run. Read the first error, not the last.
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('start', 'stop', 'status')][string]$Action,
    [ValidateSet('scada', 'historian', 'opcua')][string]$Target = 'scada'
)
$ErrorActionPreference = 'Continue'

$net = 'vigilimen-plant_net_supervisory'
$cfg = @{
    scada     = @{ name = 'vigilimen-relay-scada';     svc = 'scada';     host = 1881;  port = 1881 }
    historian = @{ name = 'vigilimen-relay-historian'; svc = 'historian'; host = 15432; port = 5432 }
    opcua     = @{ name = 'vigilimen-relay-opcua';     svc = 'opcua-sup'; host = 14840; port = 4840 }
}

switch ($Action) {
    'start' {
        $c = $cfg[$Target]
        docker rm -f $c.name 2>$null | Out-Null
        docker run -d --rm --name $c.name -p "127.0.0.1:$($c.host):$($c.port)" alpine/socat "tcp-listen:$($c.port),fork,reuseaddr" "tcp:$($c.svc):$($c.port)" | Out-Null
        docker network connect $net $c.name
        Write-Host "relay up: 127.0.0.1:$($c.host)  ->  $($c.svc):$($c.port)"
    }
    'stop' {
        foreach ($k in $cfg.Keys) { docker rm -f $cfg[$k].name 2>$null | Out-Null }
        Write-Host "relays removed"
    }
    'status' {
        docker ps --filter "name=vigilimen-relay" --format "{{.Names}}  {{.Ports}}"
    }
}
