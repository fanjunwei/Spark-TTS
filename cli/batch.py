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
import time
import requests


api_servers = [
    "http://192.168.1.3:8000",
]


def call_tts_api(server_url: str, text: str, audio_path: str, save_path: str):
    """调用TTS API服务并等待结果

    Args:
        server_url: API服务器地址
        text: 要转换的文本
        audio_path: 输入音频文件路径
        save_path: 输出音频保存路径
    """
    try:
        # 1. 创建任务
        filename = os.path.basename(audio_path)

        # 尝试方法一：使用files和json
        files = {
            "audio_file": (filename, open(audio_path, "rb")),
        }
        body = {
            "text": text,
        }
        response = requests.post(
            f"{server_url}/tts/create", files=files, data=body
        )
        response.raise_for_status()

        task_id = response.json()["task_id"]
        logging.info(f"Created task {task_id}")

        # 2. 轮询任务状态
        error_count = 0
        while True:
            response = requests.get(f"{server_url}/tts/status/{task_id}")
            if response.status_code != 200:
                time.sleep(1)
                error_count += 1
                if error_count > 10:
                    raise Exception("Failed to get task status")
                continue
            status = response.json()

            if status["status"] == "completed":
                break
            elif status["status"] == "failed":
                raise Exception(f"Task failed: {status.get('error')}")

            logging.info(f"Task {task_id} is still processing, waiting...")
            time.sleep(5)  # 等待5秒后再次查询

        # 3. 下载生成的音频文件
        logging.info(f"Downloading result for task {task_id}")
        error_count = 0
        while True:
            response = requests.get(f"{server_url}/tts/download/{task_id}")
            if response.status_code != 200:
                time.sleep(1)
                error_count += 1
                if error_count > 10:
                    raise Exception("Failed to download audio")
                continue
            else:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                break

        logging.info(f"Successfully saved audio to {save_path}")

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Error during API call: {str(e)}")
        raise


def main(dir_path: str):
    health_servers = []
    for server_url in api_servers:
        try:
            logging.info(f"Checking TTS API server: {server_url}")
            response = requests.get(f"{server_url}/tts/health", timeout=10)
            if response.status_code == 200:
                health_servers.append(server_url)
        except Exception as e:
            logging.error(f"Error calling TTS API: {str(e)}")
            continue
    logging.info(f"Available TTS API servers: {health_servers}")
    if len(health_servers) == 0:
        logging.error("No available TTS API servers")
        return

    files = os.listdir(dir_path)
    files.sort()
    for file in files:
        if file.endswith(".txt"):
            with open(os.path.join(dir_path, file), "r") as f:
                text = f.read()
            index, audio_name = file.split(".")[0].split("_")
            index = int(index)
            server_index = index % len(health_servers)
            server_url = health_servers[server_index]
            audio_path = os.path.join(dir_path, f"{audio_name}.mp3")
            if not os.path.exists(audio_path):
                audio_path = os.path.join(dir_path, f"{audio_name}.wav")
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file {audio_path} does not exist")
            print(audio_path)
            print(text)
            save_path = os.path.join(dir_path, f"output_{index:03d}.wav")
            if os.path.exists(save_path):
                logging.info(f"Skipping {save_path} because it already exists")
                continue
            try:
                for i in range(3):
                    try:
                        call_tts_api(server_url, text, audio_path, save_path)
                        break
                    except Exception as e:
                        logging.error(f"Error calling TTS API: {str(e)}")
                        time.sleep(1)
            except Exception as e:
                logging.error(f"Error calling TTS API: {str(e)}")
                continue


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir_path", type=str, required=True)
    args = parser.parse_args()
    main(args.dir_path)
