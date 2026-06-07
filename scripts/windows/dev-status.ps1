param([Parameter(Mandatory=$true)][string]$ServerIP)

$remote = "dev@$ServerIP"
ssh $remote "cd /srv/devshare/myapp/infra/docker && docker compose ps"
