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


import argparse
import logging
import os
from pathlib import Path

import soundfile as sf
import torch

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


def main(dir_path: str):
    files = os.listdir(dir_path)
    files.sort()
    for file in files:
        if file.endswith(".txt"):
            with open(os.path.join(dir_path, file), "r") as f:
                text = f.read()
            index, audio_name = file.split(".")[0].split("_")
            audio_path = os.path.join(dir_path, f"{audio_name}.mp3")
            print(audio_path)
            print(text)
            save_path = os.path.join(dir_path, f"output_{index}.wav")
            if os.path.exists(save_path):
                logging.info(f"Skipping {save_path} because it already exists")
                continue
            run_tts(text, audio_path, save_path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir_path", type=str, required=True)
    args = parser.parse_args()
    main(args.dir_path)
