#!/bin/bash

HTTP_PORT=8088

TMP_DIR=/tmp/operator-data
mkdir -p $TMP_DIR
for file in results/mirroring-1-probe-*.csv; do
	base="$(date +%s.%N)_0_data"
	cp "$file" "$TMP_DIR/${base}.csv"
	# create semaphore file
	touch "$TMP_DIR/${base}.csv.sem"
done


NAME=$(date +%s)

docker run --rm -d --name mmt-mongo-$NAME -p127.0.0.100:27019:27017 mongo:7.0

docker run --rm -it -v$TMP_DIR:/opt/mmt/probe/result/report/online \
	--network=host --name mmt-operator-$NAME  \
	ghcr.io/montimage/mmt-operator:v1.7.7     \
	-Xport_number=$HTTP_PORT \
	-Xdatabase_server.host=127.0.0.100 -Xdatabase_server.port=27019

# stop mongodb
docker stop "mmt-mongo-$NAME"
rm -rf "$TMP_DIR"