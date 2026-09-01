#!/bin/sh
set -e

resolver="$(awk '/^nameserver/{print $2; exit}' /etc/resolv.conf)"
if [ -n "$resolver" ]; then
  sed -i "s/__DNS_RESOLVER__/$resolver/" /etc/nginx/conf.d/default.conf
fi
