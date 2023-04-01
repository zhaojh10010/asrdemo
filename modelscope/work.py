import io
import traceback
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import asyncio
import json
from fastapi import FastAPI
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi import Response
from starlette.websockets import WebSocketState as WebSocketState
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import base64
import wave
import time
import datetime
import os
import shutil
import math
from pydantic import BaseModel
from typing import Optional, Union
import json
from enum import IntEnum
from pydub import AudioSegment

class ASRRequest(BaseModel):
    """
    request body example
    {
        "audio": "exSI6ICJlbiIsCgkgICAgInBvc2l0aW9uIjogImZhbHNlIgoJf...",
        "audio_format": "wav",
        "sample_rate": 16000,
        "lang": "zh_cn",
        "punc":false
    }
    """
    audio: str
    audio_format: str
    sample_rate: int
    lang: str
    punc: Optional[bool] = None

class Message(BaseModel):
    description: str
class AsrResult(BaseModel):
    transcription: str
class ASRResponse(BaseModel):
    """
    response example
    {
        "success": true,
        "code": 0,
        "message": {
            "description": "success" 
        },
        "result": {
            "transcription": "你好，飞桨"
        }
    }
    """
    success: bool
    code: int
    message: Message
    result: AsrResult

class ErrorResponse(BaseModel):
    """
    response example
    {
        "success": false,
        "code": 0,
        "message": {
            "description": "Unknown error occurred."
        }
    }
    """
    success: bool
    code: int
    message: Message


# p = pipeline('auto-speech-recognition', 'damo/speech_UniASR_asr_2pass-cn-en-moe-16k-vocab8358-tensorflow1-online'
#              , device='gpu')

p = pipeline(
    task=Tasks.auto_speech_recognition,
    model='damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
    vad_model='damo/speech_fsmn_vad_zh-cn-16k-common-pytorch',
    vad_model_revision="v1.1.8",
    device='gpu'
#     punc_model='damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch',
#     punc_model_revision="v1.1.6"
    )

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])

@app.websocket('/paddlespeech/asr/streaming')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    all_text = ""
    i = 0
    try:
        while True:
            assert websocket.application_state == WebSocketState.CONNECTED
            message = await websocket.receive()
            websocket._raise_on_disconnect(message)
            if "text" in message:
                message = json.loads(message["text"])
                if 'signal' not in message:
                    resp = {"status": "ok", "message": "no valid json data"}
                    await websocket.send_json(resp)
                if message['signal'] == 'start':
                    resp = {"status": "ok", "signal": "server_ready"}
                    all_text = ""
                    i = 0
                    await websocket.send_json(resp)
                elif message['signal'] == 'end':
                    # 取出所有数据
                    resp = {
                        "status": "ok",
                        "signal": "finished",
                        'result': all_text,
                        'times': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    await websocket.send_json(resp)
                    break
                elif message['signal'] == 'reset':
                    all_text = ""
                    i = 0
                    resp = {"status": "ok", "signal": "cache_cleared", 'result': ''}
                    await websocket.send_json(resp)
                else:
                    resp = {"status": "ok", "message": "no valid json data"}
                    await websocket.send_json(resp)
            elif "bytes" in message:
                i = i + 1
                message = message["bytes"]
                #只加vad
                #{'text': 'english', 'text_postprocessed': 'english'}
                #再加punc
                #首次:{'time_stamp': [], 'sentences': []}
                #有语音:{'text': '我认世界。', 'text_postprocessed': '我认世界', 'sentences': []}
                asr_results = p(message, audio_fs=16000)
                print("================")
                print(asr_results)
                print("================")
                if asr_results and 'text' in asr_results:
                    all_text = all_text + asr_results['text']
                
                resp = {'result': all_text}
                await websocket.send_json(resp)
    except WebSocketDisconnect as e:
        print("Error: ".str(e))

@app.post("/paddlespeech/asr/talcs", response_model=Union[ASRResponse, ErrorResponse])
def asr(request_body: ASRRequest):
    try:
        audio_data = request_body.audio
        decoded_data = base64.b64decode(audio_data)
        audio = AudioSegment.from_file(io.BytesIO(decoded_data), format='wav')

        audio_save_path = './audios/audio_file_'+str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        audio_name = audio_save_path +'.wav'
        tmp_dir = audio_save_path + '/seg'
        os.makedirs(tmp_dir, exist_ok=True)
        audio.export(audio_name, format='wav')

        # with wave.open(audio_name, 'wb') as audio_file:
        #     audio_file.setnchannels(1) # 单声道
        #     audio_file.setsampwidth(2) # 采样位宽为2字节即16bits
        #     audio_file.setframerate(16000) # 采样率为16000 Hz
        #     audio_file.writeframes(decoded_data)
        

        # 加载音频文件
        audio_file = AudioSegment.from_file(audio_name, format='wav')

        # 获取音频文件时长
        duration = len(audio_file)
        print('共长: {}'.format(duration))
        # 定义分割时间间隔
        segment_interval = 20 * 1000 # 20秒，单位为毫秒
        
        # 解析结果
        text = ''

        # 分割音频文件并保存到目录下
        for i in range(0, duration, segment_interval):
            # 计算分割开始和结束时间
            start_time = i
            end_time = min(i+segment_interval, duration)

            # 分割音频文件
            segment = audio_file[start_time:end_time]

            # 保存分割后的子音频文件
            seg_file = os.path.join(tmp_dir, f'w{i}.wav')
            segment.export(seg_file, format='wav')
        #     text_seg = p(audio_in=seg_file)
        #     print('解析段-{}:{}'.format('w'+str(i), text_seg))
        #     text = text + text_seg

            with open(seg_file, 'rb') as f:
                binary_data = f.read()
                text_seg = p(audio_in=binary_data)['text']# 这东西不能直接传路径!
                text = text + text_seg
        response = {
        "success": True,
        "code": 200,
        "message": {
                "description": "success"
        },
        "result": {
                "transcription": text
        }
        }
        print('ASR Result: \n{}'.format(text))
        
        # shutil.rmtree(tmp_dir)
    except ServerBaseException as e:
        response = failed_response(e.error_code, e.msg)
    except BaseException:
        response = failed_response(ErrorCode.SERVER_UNKOWN_ERR)
        traceback.print_exc()

    return response


class ErrorCode(IntEnum):
    SERVER_OK = 200  # success.

    SERVER_PARAM_ERR = 400  # Input parameters are not valid.
    SERVER_TASK_NOT_EXIST = 404  # Task is not exist.

    SERVER_INTERNAL_ERR = 500  # Internal error.
    SERVER_NETWORK_ERR = 502  # Network exception.
    SERVER_UNKOWN_ERR = 509  # Unknown error occurred.

class ServerBaseException(Exception):
    """ Server Base exception
    """

    def __init__(self, error_code, msg=None):
        #if msg:
        #log.error(msg)
        msg = msg if msg else ErrorMsg.get(error_code, "")
        super(ServerBaseException, self).__init__(error_code, msg)
        self.error_code = error_code
        self.msg = msg
        traceback.print_exc()

ErrorMsg = {
    ErrorCode.SERVER_OK: "success.",
    ErrorCode.SERVER_PARAM_ERR: "Input parameters are not valid.",
    ErrorCode.SERVER_TASK_NOT_EXIST: "Task is not exist.",
    ErrorCode.SERVER_INTERNAL_ERR: "Internal error.",
    ErrorCode.SERVER_NETWORK_ERR: "Network exception.",
    ErrorCode.SERVER_UNKOWN_ERR: "Unknown error occurred."
}


def failed_response(code, msg=""):
    """Interface call failure response

    Args:
        code (int): error code number
        msg (str, optional): Interface call failure information. Defaults to "".

    Returns:
        Response (json): failure json information.
    """

    if not msg:
        msg = ErrorMsg.get(code, "Unknown error occurred.")

    res = {"success": False, "code": int(code), "message": {"description": msg}}

    return Response(content=json.dumps(res), media_type="application/json")

if __name__ == '__main__':
    uvicorn.run(app=app, host='0.0.0.0', port=9000)