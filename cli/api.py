# Copyright (c) 2025 SparkAudio
#               2025 Xinsheng Wang (w.xinshawn@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
from pathlib import Path
import uuid
import os
from typing import Dict

import soundfile as sf
import torch
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import uvicorn
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

from cli.SparkTTS import SparkTTS


def run_tts(text: str, audio_path: str, save_path: str):
    """Perform TTS inference and save the generated audio."""
    logging.info(f"Saving audio to: {save_path}")
    model_dir = Path(__file__).parent.parent / "pretrained_models/Spark-TTS-0.5B"
    model_dir = str(model_dir)
    # Ensure the save directory exists

    # Convert device argument to torch.device
    device = torch.device("cpu")
    logging.info("GPU acceleration not available, using CPU")

    # Initialize the model
    model = SparkTTS(model_dir, device)

    logging.info("Starting inference...")

    # Perform inference and save the output audio
    with torch.no_grad():
        wav = model.inference(
            text,
            audio_path,
            prompt_text=None,
            gender=None,
            pitch=None,
            speed=None,
        )
        sf.write(save_path, wav, samplerate=16000)

    logging.info(f"Audio saved at: {save_path}")


# 存储任务状态和结果
tasks: Dict[str, Dict] = {}
executor = ThreadPoolExecutor(max_workers=2)


class TextRequest(BaseModel):
    text: str


app = FastAPI()


def process_tts(task_id: str, audio_file_path: str, text: str, output_path: str):
    try:
        run_tts(text, audio_file_path, output_path)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["output_path"] = output_path
        input_path = audio_file_path
        if os.path.exists(input_path):
            os.remove(input_path)
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


@app.post("/tts/create")
async def create_tts_task(text: str = Form(...), audio_file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())

    # 创建临时目录存储文件
    os.makedirs("temp", exist_ok=True)
    input_path = f"temp/{task_id}_input{os.path.splitext(audio_file.filename)[1]}"
    output_path = f"temp/{task_id}_output.wav"

    # 保存上传的音频文件
    with open(input_path, "wb") as f:
        f.write(await audio_file.read())

    # 创建任务
    tasks[task_id] = {
        "status": "processing",
        "input_path": input_path,
        "output_path": output_path,
    }

    # 在后台执行TTS处理
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, process_tts, task_id, input_path, text, output_path)

    return {"task_id": task_id}


@app.get("/tts/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    return {"status": task["status"], "error": task.get("error")}


@app.get("/tts/download/{task_id}")
async def download_audio(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")

    return FileResponse(task["output_path"])


@app.get("/tts/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
