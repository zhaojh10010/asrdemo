#!/bin/bash
go() {
 nohup python /work.py >> /work.log 2>&1 &
}
stop() {
 pkill -f work.py
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