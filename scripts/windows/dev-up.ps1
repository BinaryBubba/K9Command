param(
  [Parameter(Mandatory=$true)][string]$ServerIP
)

$remote = "dev@$ServerIP"
$cmd = "cd /srv/devshare/myapp/infra/docker && docker compose up -d && docker compose ps"
ssh $remote $cmd

Start-Process "https://k9command.maniacranch.com/"
