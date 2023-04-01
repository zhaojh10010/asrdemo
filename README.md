# asrdemo
语音识别demo(后端使用modelscope的Paraformer识别语音, 百度飞浆paddle punctual补充标点)

# Requirements
使用docker安装对应的服务端环境

[Paddle docker环境安装](https://www.paddlepaddle.org.cn/install/quick?docurl=/documentation/docs/zh/install/docker/linux-docker.html)

[Modelscope环境安装](https://modelscope.cn/docs/%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85)

> 两个镜像分别需要15G+ 和20G+的磁盘空间..加上容器本身至少需要70G+空间, 如果没有多余空间只有考虑按照教程自己配置环境

docker容器参数示例
- [Paddle]
端口可以去`/home/PaddleSpeech/demos/streaming_asr_server/conf/punc_application.yaml`里面配置
```shell
docker run -itd --name paddle --gpus all -v $PWD:/mnt -p 36000:8080 -p 36100:8900 paddlecloud/paddlespeech:develop-gpu-cuda11.2-cudnn8-c8196d
```

- [Modelscope]
```shell
docker run -itd --name modelscope --gpus all -p 37000:9000 registry.cn-hangzhou.aliyuncs.com/modelscope-repo/modelscope:ubuntu20.04-cuda11.3.0-py37-torch1.11.0-tf1.15.5-1.4.1
```

# 服务端启动脚本
Modelscope的Paraformer模型比百度飞浆的效果更好, 所以优先建议使用Modelscope语音识别
### Modelscope服务启动
1. 把`work.py`和`asr.sh`扔到根目录`/`里面
  - `docker cp asr.sh modelscope:/asr.sh`
  - `docker cp work.py modelscope:/work.py`
2. 进入容器操作
  - `docker exec -it modelscope /bin/bash`
  - `chmod +x asr.sh`
3. 安装一些执行环境
  - `pip config set global.index-url https://mirror.sjtu.edu.cn/pypi/web/simple`
  - `pip install uvicorn[standard]`
  - `pip install pydub`
  - `pip install pydantic`
4. 启动/停止服务, 默认端口`9000`
  - `/asr.sh go` or `/asr.sh stop` 来启动或停止服务
5. 容器外启动
  - `docker exec -d modelscope sh -c "/asr.sh go"`


### 百度标点补充服务启动
1. 将脚本扔到docker容器里面去
  - `docker cp punc.sh paddle:/punc.sh`
2. 进入容器操作
  - `docker exec -it modelscope /bin/bash`
  - `chmod +x /punc.sh`
3. 修改punctual服务端口, 默认`8080`
  - `vim /home/PaddleSpeech/demos/streaming_asr_server/conf/punc_application.yaml`
  - 将`port`修改为你映射的端口如`8080`
4. 启动/停止服务
  - `/punc.sh go` or `/punc.sh stop` 来启动或停止服务
5. 容器外启动
  - `docker exec -d paddle sh -c "/punc.sh go"`


# Model References
[Modelscope](https://modelscope.cn/models/damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/summary)
[Paddle](https://github.com/PaddlePaddle/PaddleSpeech/tree/develop/demos/streaming_asr_server)
