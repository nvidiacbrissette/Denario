# Flatiron NIM + Denario on-prem.

First we get onto Rusty.

```
ssh -p 61022 cbrissette@gateway.flatironinstitute.org
ssh rusty
```

Then we need to create our apptainer container out of Nemotron.

```
module load apptainer
module load modules/2.4-20250724
module load python/3.12.9
export NVIDIA_API_KEY=[YOUR NVIDIA API KEY]
export APPTAINER_DOCKER_USERNAME='$oauthtoken'
export APPTAINER_DOCKER_PASSWORD=$NVIDIA_API_KEY
apptainer pull nemotron-3-nano.sif docker://nvcr.io/nim/nvidia/nemotron-3-nano:latest
```

This will take quite some time. Your pipe may break. Just be patient. Go to the gym or something.  Before jumping on our node, let’s make sure we have Denario. Note the current NIM-enabled version lives on a fork here: nvidiacbrissette/Denario: Modular Multi-Agent System for Scientific Research Assistance - forked. This is likely to change later.

```
git clone https://github.com/nvidiacbrissette/Denario.git
```

After that you can enter your actual node. We will do an interactive session here before launching the NIM.

```
srun -p gpu --gpus=1 --reservation=rocky9 --time=01:00:00 --pty bash -i
```

Once you are on, run nvidia-smi to make sure you have GPU resources. You should see something like this:

```
[cbrissette@workergpu179 ~]$ nvidia-smi
Thu Mar 12 12:17:58 2026
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 590.48.01      CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA RTX PRO 6000 Blac...    Off |   00000000:15:00.0 Off |                    0 |
| N/A   30C    P8             33W /  600W |       0MiB /  97887MiB |      0%      Default |
|                                         |                        |             Disabled |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+
```

Then we need to bind some file-paths to our Apptainer container because Apptainer containers are immutable by default. You can do something similar with ‘sandbox’ mode, though we aren’t using that here.

```
export LOCAL_NIM_CACHE=/mnt/home/cbrissette/nimcache
mkdir $LOCAL_NIM_CACHE
export NIM_WORKSPACE=/mnt/home/cbrissette/nimworkspace
mkdir $NIM_WORKSPACE
apptainer run --nv --env NGC_API_KEY=$NVIDIA_API_KEY --bind $LOCAL_NIM_CACHE:/opt/nim/.cache --bind $NIM_WORKSPACE:/opt/nim/workspace nemotron-3-nano.sif > nim.log 2>&1 &
```

If you have run this before you may get some weird behavior. This can sometimes be mitigated by clearing our workspace and cache before running.

```
rm -r nimcache/*
rm -r nimworkspace/*
```

Once this is up and running we can test it with the following commands:
```
tail -f nim.log
```
```
curl -X 'POST' \
'http://0.0.0.0:8000/v1/chat/completions' \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
    "model": "nvidia/nemotron-3-nano",
    "messages": [{"role":"user", "content":"Which number is larger, 9.11 or 9.8?"}],
    "max_tokens": 64
}'
```

Now we can run Denario! But wait! We need to make a venv and get required packages.

```
cd Denario
sh setup_env.sh
```

This takes a bit of time.

```
export NIM_BASE_URL="http://localhost:8000/v1"
export NVIDIA_API_KEY="EMPTY"
cd examples
python3 nemotron-workflow.py
```

You should now see the workflow run!
