#!/bin/sh
set -e

resolver="$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)"
if [ -n "$resolver" ]; then
  sed -i "s/__DNS_RESOLVER__/$resolver/" /etc/nginx/conf.d/default.conf
fi

# nginx'in kendi resolver mekanizmasi, normal uygulamalarin (getaddrinfo)
# aksine, /etc/resolv.conf'taki "search" alan adlarini bare hostname'lere
# OTOMATIK EKLEMIYOR - verdigimiz stringi harfi harfine sorguyor. Docker
# Compose'da "backend" bare hali zaten dogrudan cozulur ama Kubernetes'te
# CoreDNS'in gercek kaydi "backend.<namespace>.svc.cluster.local" - bu
# yuzden k8s'te tam nitelikli adi kullanmamiz gerekiyor.
search_domain="$(awk '/^search/{for(i=2;i<=NF;i++){if($i ~ /svc\.cluster\.local/){print $i; exit}}}' /etc/resolv.conf)"
if [ -n "$search_domain" ]; then
  backend_host="backend.$search_domain"
else
  backend_host="backend"
fi
sed -i "s/__BACKEND_HOST__/$backend_host/" /etc/nginx/conf.d/default.conf
