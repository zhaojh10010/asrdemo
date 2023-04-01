#!/bin/bash
st=/home/PaddleSpeech/demos/streaming_asr_server

punc() {
  cd ${st}
  nohup paddlespeech_server start --config_file conf/punc_application.yaml &>> /home/punc.log &
  echo Server started
}

stoppunc() {
  pkill -f conf/punc_application.yaml
  echo Server ended
}

case "$1" in
 go)
  punc
  ;;
 stop)
  stoppunc
  ;;
 *)
 echo $"Usage: $0 {go|stop}"
 ;;
esac