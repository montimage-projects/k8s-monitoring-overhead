#!/usr/bin/env bash
set -euo pipefail

NS="testbed"
URL="http://192.168.1.26:30080/"
ITERATIONS=20

# remote kubectl
function rkubectl(){
	ssh -p 2222 montimage@localhost -- kubectl -n "$NS" "$@"
}

function deploys(){
	local i
	
	for i in "$@"; do
		echo "deploying $i"
		cat "./manifest/$i" | rkubectl apply -f-
	done
}

function undeploys(){
	local i
	
	for i in "$@"; do
		echo "undeploying $i"
		cat "./manifest/$i" | rkubectl delete -f- --ignore-not-found
	done
}

function remote_logs(){
	rkubectl exec "$@" -- "bash -c 'cat /opt/mmt/probe/result/report/online/*.csv'"
}

function traffic(){
	local ID
	
	ID=$1
	# https://manpages.ubuntu.com/manpages/jammy/man1/hey.1.html
	# -c: number of concurrencies
	# -q: queries per second
	# -n: number of requests to run
	sleep 5
	echo "generating trafic to $URL"
	hey -n 110 -c 1 -q 3 -o csv "$URL" > "./results/$ID-latency.csv"
	#sleep 3600
}

rm -rf results
mkdir -p results

rkubectl delete namespace "$NS" || true
rkubectl create namespace "$NS" || true

#
# scenario 0: baseline
function baseline(){
	local ID
	local MANIFEST
	
	ID="baseline-$1"
	date
	echo "=== Baseline iteration $ID ==="

	MANIFEST="http-baseline.yaml haproxy.yaml"

	undeploys $MANIFEST
	deploys $MANIFEST

	rkubectl rollout status deployment/haproxy
	rkubectl rollout status deployment/http-server

	traffic "$ID"
	
	undeploys $MANIFEST
}


# scenario 1: mirroring
function mirroring(){
	local ID
	local MANIFEST
	
	ID="mirroring-$1"
	date
	echo "=== Mirroring iteration $ID ==="

	MANIFEST="mmt-gateway.yaml http-mmt-sidecar.yaml haproxy-mmt.yaml mmt-node-worker.yaml mmt-node-master.yaml"

	undeploys $MANIFEST
	deploys $MANIFEST


	rkubectl rollout status deployment/mmt-node-worker
	rkubectl rollout status deployment/mmt-node-master
	rkubectl rollout status deployment/mmt-gw-probe
	rkubectl rollout status deployment/haproxy
	rkubectl rollout status deployment/http-server

	traffic "$ID"
	
	# wait for all mmt-probes output (each 5 seconds)
	sleep 5

	remote_logs -c mmt-probe deployment/mmt-gw-probe    > ./results/$ID-probe-1.csv
	remote_logs -c mmt-probe deployment/mmt-node-worker > ./results/$ID-probe-2.csv
	remote_logs -c mmt-probe deployment/haproxy         > ./results/$ID-probe-3.csv
	remote_logs -c mmt-probe deployment/mmt-node-master > ./results/$ID-probe-4.csv
	remote_logs -c mmt-probe deployment/http-server     > ./results/$ID-probe-5.csv

	undeploys $MANIFEST
}


# scenario 2: proxying
function proxying(){
	local ID
	local MANIFEST
	
	ID="proxying-$1"
	date
	echo "=== Proxying iteration $ID ==="

	MANIFEST="mmt-gateway.yaml http-envoy-sidecar.yaml haproxy-mmt.yaml mmt-node-worker.yaml mmt-node-master.yaml"

	undeploys $MANIFEST
	deploys $MANIFEST

	rkubectl rollout status deployment/mmt-node-worker
	rkubectl rollout status deployment/mmt-node-master
	rkubectl rollout status deployment/mmt-gw-probe
	rkubectl rollout status deployment/haproxy
	rkubectl rollout status deployment/http-server

	traffic "$ID"
	
	# wait for all mmt-probes output (each 5 seconds)
	sleep 5

	remote_logs -c mmt-probe deployment/mmt-gw-probe    > ./results/$ID-probe-1.csv
	remote_logs -c mmt-probe deployment/mmt-node-worker > ./results/$ID-probe-2.csv
	remote_logs -c mmt-probe deployment/haproxy         > ./results/$ID-probe-3.csv
	remote_logs -c mmt-probe deployment/mmt-node-master > ./results/$ID-probe-4.csv
	remote_logs -c mmt-probe deployment/http-server     > ./results/$ID-probe-5.csv


	undeploys $MANIFEST
}


# scenario 3: moving lateral
function hijack(){
	local ID
	local MANIFEST
	
	ID="hijack-$1"
	date
	echo "=== HIJACK iteration $ID ==="

	MANIFEST="mmt-gateway.yaml http-mmt-sidecar.yaml haproxy-mmt-infected.yaml mmt-node-worker.yaml mmt-node-master.yaml"

	undeploys $MANIFEST
	deploys $MANIFEST

	rkubectl rollout status deployment/mmt-node-worker
	rkubectl rollout status deployment/mmt-node-master
	rkubectl rollout status deployment/mmt-gw-probe
	rkubectl rollout status deployment/haproxy
	rkubectl rollout status deployment/http-server

	traffic "$ID"
	
	# wait for all mmt-probes output (each 5 seconds)
	sleep 5

	remote_logs -c mmt-probe deployment/mmt-gw-probe    > ./results/$ID-probe-1.csv
	remote_logs -c mmt-probe deployment/mmt-node-worker > ./results/$ID-probe-2.csv
	remote_logs -c mmt-probe deployment/haproxy         > ./results/$ID-probe-3.csv
	remote_logs -c mmt-probe deployment/mmt-node-master > ./results/$ID-probe-4.csv
	remote_logs -c mmt-probe deployment/http-server     > ./results/$ID-probe-5.csv


	undeploys $MANIFEST
}

#for iter in $(seq 1 $ITERATIONS); do
#	sleep 10
#	baseline $iter
#done
#
#
#for iter in $(seq 1 $ITERATIONS); do
#	sleep 10
#	mirroring $iter
#done
#
#
#for iter in $(seq 1 $ITERATIONS); do
#	sleep 10
#	proxying $iter
#done


# only one run is enough to collect the topology
sleep 10
hijack 1
