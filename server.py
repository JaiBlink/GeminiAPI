import base64
import json
import urllib.parse
from flask import Flask
import os
from google.oauth2.credentials import Credentials
import google.generativeai as genai
from flask import request, make_response
from flask_cors import CORS, cross_origin
from datetime import datetime
import requests
import urllib

SCOPES = ['https://www.googleapis.com/auth/generative-language.tuning']
TOKEN_PATH = r"C:\Users\poullow\Documents\Python\Flask\GeminiAPI\token.json"
VOICE_ID = "3HA9GDFCLP50aN7Gd4YC"
YOUR_XI_API_KEY = "b3dafbbbc8ac40f1dc2dedb0407efa75"
ELEVEN_LABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream/with-timestamps?enable_logging=true&optimize_streaming_latency=2&output_format=mp3_22050_32"
SERVER_POINT_URL = "http://192.168.2.29:3020"

SYLLABIFIED_AUDIO_FILE_SAVE_PATH = r"C:\Users\poullow\Documents\Python\Flask\GeminiAPI\static\audio\syllabified"
VO_AUDIO_FILE_SAVE_PATH = r"C:\Users\poullow\Documents\Python\Flask\GeminiAPI\static\audio\vo"

app = Flask(__name__, static_url_path='', static_folder='static/')
app.config['CORS_HEADERS'] = 'Content-Type'
cors = CORS(app)

# AUDIO_FILE_SAVE_PATH = r"C:\Users\poullow\Documents\Python\Flask\GeminiAPI\audio"

def gen_audio(res_str):
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": YOUR_XI_API_KEY
    }

    data = {
        "text": (res_str),
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(
        ELEVEN_LABS_URL,
        json=data,
        headers=headers,
        stream=True
    )

    if response.status_code != 200:
        print(f"Error encountered, status: {response.status_code}, "
            f"content: {response.text}")
        quit()

    audio_bytes = b""
    characters = []
    character_start_times_seconds = []
    character_end_times_seconds = []

    for line in response.iter_lines():
        if line:  # filter out keep-alive new line
            # convert the response which contains bytes into a JSON string from utf-8 encoding
            json_string = line.decode("utf-8")

            # parse the JSON string and load the data as a dictionary
            response_dict = json.loads(json_string)

            # the "audio_base64" entry in the dictionary contains the audio as a base64 encoded string, 
            # we need to decode it into bytes in order to save the audio as a file
            audio_bytes_chunk = base64.b64decode(response_dict["audio_base64"])
            audio_bytes += audio_bytes_chunk
            
            if response_dict["alignment"] is not None:
                characters.extend(response_dict["alignment"]["characters"])
                character_start_times_seconds.extend(response_dict["alignment"]["character_start_times_seconds"])
                character_end_times_seconds.extend(response_dict["alignment"]["character_end_times_seconds"])

    return audio_bytes, characters, character_start_times_seconds, character_end_times_seconds

@app.route("/")
def index():
    return "App running"

@app.route("/get_text", methods=["POST"])
def return_demo_str():
    return "Helper string"

@app.route("/ai", methods=["POST"])
@cross_origin(origin='localhost',headers=['Content-Type','Authorization'])
def get_text():
    print("---------------------------------------")
    print(request.data)
    try:
        input_text = json.loads(request.data.decode('utf-8')).get("text", "")
        if(input_text == ""):
            return "invalid request"
        creds = Credentials.from_authorized_user_file(filename=TOKEN_PATH, scopes=SCOPES)
        genai.configure(credentials=creds)
        # model = genai.GenerativeModel(f'tunedModels/specialeducator-28ieley15kfu')
        model = genai.GenerativeModel(f'tunedModels/specialeducatorwithspellcheck-hzyva6lc35')

        result = model.generate_content(input_text)
        res = {
            'msg': 'success',
            'response': result.text
        }
        print(f"Resoponse :: {res}")
        return json.dumps(res)
    except Exception as e:
        print(e)
        return "invalid request"

@app.route("/getSyllabifiedVO", methods=["POST"])
@cross_origin(origin='localhost',headers=['Content- Type','Authorization'])
def get_syllabified_text_with_vo():
    input_text = json.loads(request.data.decode('utf-8')).get("text", "")
    if(input_text == ""):
        return "invalid request"

    creds = Credentials.from_authorized_user_file(filename=TOKEN_PATH, scopes=SCOPES)
    genai.configure(credentials=creds)
    # model = genai.GenerativeModel(f'tunedModels/specialeducator-28ieley15kfu')
    model = genai.GenerativeModel(f'tunedModels/specialeducatorwithspellcheck-hzyva6lc35')
    result = model.generate_content(input_text)
    res_str = result.text

    audio_bytes, characters, character_start_times_seconds, character_end_times_seconds = gen_audio(res_str)

    audio_path = os.path.join(SYLLABIFIED_AUDIO_FILE_SAVE_PATH, f"tts_syllable_vo_{VOICE_ID}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3")
    with open(audio_path, 'wb') as f:
        f.write(audio_bytes)

    strings = []
    str_start_time = []
    str_end_time = []
    buff_str = ""
    for charVal, startTime, endTime in zip(characters, character_start_times_seconds, character_end_times_seconds):
        if(charVal == "-"):
            strings.append(buff_str)
            str_start_time.append(startTime)
            str_end_time.append(endTime)
            buff_str = ""
            continue
        buff_str += charVal

    strings.append(buff_str)
    str_start_time.append(character_start_times_seconds[-1])
    str_end_time.append(character_end_times_seconds[-1])

    return json.dumps({
        "response_str": res_str,
        "strings": strings,
        "str_start_times_seconds": str_start_time,
        "str_end_times_seconds": str_end_time,
        "vo_url": f"{SERVER_POINT_URL}/audio/syllabified/{os.path.basename(audio_path)}"
    })

@app.route("/getVOwithTimeStamp", methods=["POST"])
@cross_origin(origin='localhost',headers=['Content- Type','Authorization'])
def get_vo_with_timestamp():
    input_text = json.loads(request.data.decode('utf-8')).get("text", "")
    if(input_text == ""):
        return "invalid request"
    audio_bytes, characters, character_start_times_seconds, character_end_times_seconds = gen_audio(input_text)

    audio_path = os.path.join(VO_AUDIO_FILE_SAVE_PATH, f"tts_vo_{VOICE_ID}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3")
    with open(audio_path, 'wb') as f:
        f.write(audio_bytes)

    strings = []
    str_start_time = []
    str_end_time = []
    buff_str = ""
    for charVal, startTime, endTime in zip(characters, character_start_times_seconds, character_end_times_seconds):
        if(charVal == " "):
            strings.append(buff_str)
            str_start_time.append(startTime)
            str_end_time.append(endTime)
            buff_str = ""
            continue
        buff_str += charVal

    strings.append(buff_str)
    str_start_time.append(character_start_times_seconds[-1])
    str_end_time.append(character_end_times_seconds[-1])

    return json.dumps({
        "strings": strings,
        "str_start_times_seconds": str_start_time,
        "str_end_times_seconds": str_end_time,
        "vo_url": f"{SERVER_POINT_URL}/audio/vo/{os.path.basename(audio_path)}"
    })

app.run(debug=True, host='0.0.0.0', port=3020)