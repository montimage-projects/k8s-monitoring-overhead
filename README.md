
## Architecture

```
External client
  runs: ab

K8s cluster:
  worker-1
    HAProxy pod
    gateway-level MMT-Probe

  master
    HTTP server pod
    E0: no probe
    E1: HTTP + MMT-Probe sidecar
    E2: HTTP + Envoy sidecar

  worker-1 + master
    E3: node-level MMT-Probe DaemonSet
```

<img src=./testbed.png>

## Setup

The following must be run on the master node


### Label the worker nodes

- Get name of each node: 

```
montimage@k8s-master:~/hn/project-enforce$ kubectl get nodes
NAME          STATUS   ROLES                  AGE   VERSION
k8s-master    Ready    control-plane,master   65d   v1.35.2
k8s-worker1   Ready    worker                 65d   v1.35.2
```

## Execution

The following must be run on the host machine

### Install Hey Benchmark

https://github.com/rakyll/hey

```
sudo snap install hey
```
### Start the tests

Before running, you might need to update `rkubectl` function in `run.sh` script to
connect correctly to the master node via ssh, e.g., `ssh -p 2222 montimage@localhost`

```
bash run.sh
```

## Results

### Latency overhead

<img src=response-time.png>

### Packet overhead

<img src=traffic-packets.png>

### Network volume overhead

<img src=traffic-volume.png>

