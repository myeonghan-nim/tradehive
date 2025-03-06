#!/usr/bin/env bash
# 스크립트에서 에러가 발생하면 스크립트 실행을 중단하도록 설정
set -e

# iptables를 사용하여 방화벽 설정
# 모든 트래픽을 차단한 후 필요한 포트만 열어주는 방식
# iptables를 사용하려면 root 권한이 필요하므로 스크립트 실행 시 sudo를 사용하여 실행
# iptables를 사용하여 방화벽 설정 시 설정이 바로 적용되지만 시스템을 재부팅하면 설정이 초기화됨
# 설정을 유지하려면 설정을 저장하는 명령어를 사용해야 함

# in, out, forward(경유)의 기본 정책을 DROP으로 설정
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# in에서 상태가 ESTABLISHED, RELATED인 패킷은 ACCEPT
# ESTABLISHED: 연결이 설정된 패킷
# RELATED: 연결이 설정된 패킷과 관련된 패킷
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# in, out에 대한 loopback 트래픽은 ACCEPT
# loopback: 자기 자신으로 들어오는 트래픽
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# ------ Inbound rules ------
# HTTP(S) 포트 열기
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# ------ Outbound rules ------
# DNS, HTTP(S) 포트 열기
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 80 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT

echo "Firewall rules applied successfully."
