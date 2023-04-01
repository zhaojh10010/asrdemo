// const asrurl = "ws://yourASRserver";
// const asrMixUrl = "http://yourASRserver" + '/paddlespeech/asr/talcs'

const puncurl = "http://yourASRserver"+'/paddlespeech/text';

// const asrurl = "ws://yourASRserver";
const asrurl = "wss://yourASRserver";
const asrMixUrl = "http://yourASRserver" + '/paddlespeech/asr/talcs'

// 创建WebSocket连接
let ws;

let recording = false;

var audio = document.querySelector('#streamingFile');
var isEdge = navigator.userAgent.indexOf('Edge') !== -1 && (!!navigator.msSaveOrOpenBlob || !!navigator.msSaveBlob);
var isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
var recorder; // globally accessible
var microphone;

let myText;

let file="";

function loadAudioFile(event) {
    const file = event.target.files[0];
    if(!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        replaceLocalAudio(reader.result);
        clearText(["mixed_result_damo","mixed_result_damo_punc"]);
        getMixedRecResult(base64).then(({data}) => {
            console.log(data.result)
            let res = data.result.transcription;
            $("#mixed_result_damo").text(res);
            getPunctual(res,"#mixed_result_damo_punc");
        })
    };
    reader.readAsDataURL(file);
}

function clearText(ids) {
    ids.forEach(id => {
        document.getElementById(id).textContent = "";
    })

}

function replaceLocalAudio(src) {
    let audioFile = document.getElementById("audioFile");
    if(src)
        audioFile.src = src;
    audioFile.controls = true;
    audioFile.autoplay = true;

    if(src) {
        audioFile.src = src;
    }
}

function openWS() {
    file = "test"+new Date()+".wav"
    return new Promise((resolve, reject) => {
        if(!ws || (ws.readyState !== ws.OPEN || ws.readyState !== ws.CONNECTING)) {
            ws = new WebSocket(asrurl + "/paddlespeech/asr/streaming");
            ws.onopen = async () => {
                if(!recording) {
                    await startAudioStreaming();
                    resolve();
                }
            }
        }
    })
}

function startAudioStreaming() {
    return new Promise((resolve, reject) => {
        const audioSignal = JSON.stringify({
            name: file,
            signal: "start",
            nbest: 1
        });
        ws.send(audioSignal);//开始信号
        // 处理接收到的识别结果
        ws.onmessage = event => {
            console.log("event", event.data)
            let data = JSON.parse(event.data);
            if(data.signal === "server_ready") {
                recording = true;
                resolve();
                return;
            }

            //如何处理buffer被重置问题
            const result = data.result;
            let last = myText.length===0?0:(myText.length - 1);
            if(result && result.trim() && result.length >= myText[last].length) {
                myText[last] = result;
            } else {
                myText.push("");
            }
            $("#result").text(myText.join(""));

            if(data.signal === "finished") {
                getPunctual(myText.join(""));
            }
        };
    })
}

function getMic() {
    return new Promise((resolve, reject) => {
        if (!microphone) {
            captureMicrophone(function(mic) {
                microphone = mic;
                resolve();
            });
        }
    })
}


// 开始录音
async function startRecording() {
    await openWS();
    myText = [""];
    await getMic();
    replaceStreamingAudio();
    audio.muted = true;
    audio.srcObject = microphone;
    if(recorder) {
        recorder.destroy();
        recorder = null;
    }
    // let stream = await navigator.mediaDevices.getUserMedia({video: true, audio: true});
    var options = {
        type: 'audio',
        mimeType: 'audio/wav',
        checkForInactiveTracks: true,
        bufferSize: 16384,
        desiredSampRate: 16000,
        recorderType: StereoAudioRecorder,
        ondataavailable: (blob) => {
            console.log("ondataavailable", blob)
            sendAudioData(blob)
        },
        timeSlice: 2000,
        numberOfAudioChannels: 1,
    };
    recorder = RecordRTC(microphone, options);
    recorder.startRecording();
    recording = true;
}

// 停止录音
function stopRecording() {
    recording = false;
    if(microphone) {
        microphone.stop();
        microphone = null;
    }
    // 发送结束信号
    const endSignal = JSON.stringify({
        name: file,
        signal: "end",
        nbest: 1
    });
    ws.send(endSignal);
    recorder.stopRecording(() => {
        replaceStreamingAudio(URL.createObjectURL(recorder.getBlob()));
        setTimeout(function() {
            if(!audio.paused) return;

            setTimeout(function() {
                if(!audio.paused) return;
                audio.play();
            }, 1000);

            audio.play();
        }, 300);

        audio.play();

        blobToBase64(recorder.getBlob()).then((base64) => {
            getMixedRecResult(base64).then(({data}) => {
                console.log(data.result)
                // $("#mixed_result").text(data.result.transcription);
                getPunctual(data.result.transcription, "#mixed_result")
            })
            // console.log('Base64 data:', base64);
        }).catch((error) => {
            console.error(error);
        });
    });
}

function getMixedRecResult(base64) {
    return axios.post(asrMixUrl, {
        "audio": base64,
        "audio_format": "wav",
        "sample_rate": 16000,
        "lang": "zh_cn",
        "punc": true
    });
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const dataUrl = reader.result;
            const base64 = dataUrl.split(',')[1];
            resolve(base64);
        };
        reader.onerror = () => {
            reject(new Error('Failed to read blob data'));
        };
        reader.readAsDataURL(blob);
    });
}

// 发送PCM16数据流
function sendAudioData(data) {
    ws.send(data);
}

function getPunctual(text, eleId = "#result") {
    axios.post(puncurl, {
        text: text
    }).then(({data}) => {
        console.log(data.result.punc_text)
        $(eleId).text(data.result.punc_text);
    })
}

function replaceStreamingAudio(src) {
    var newAudio = document.createElement('audio');
    newAudio.controls = true;
    newAudio.autoplay = true;

    if(src) {
        newAudio.src = src;
    }

    var parentNode = audio.parentNode;
    parentNode.innerHTML = '';
    parentNode.appendChild(newAudio);

    audio = newAudio;
}

function captureMicrophone(callback) {
    if(microphone) {
        callback(microphone);
        return;
    }

    if(typeof navigator.mediaDevices === 'undefined' || !navigator.mediaDevices.getUserMedia) {
        alert('This browser does not supports WebRTC getUserMedia API.');

        if(!!navigator.getUserMedia) {
            alert('This browser seems supporting deprecated getUserMedia API.');
        }
    }

    navigator.mediaDevices.getUserMedia({
        audio: isEdge ? true : {
            echoCancellation: false
        }
    }).then(function(mic) {
        callback(mic);
    }).catch(function(error) {
        alert('Unable to capture your microphone. Please check console logs.');
        console.error(error);
    });
}
