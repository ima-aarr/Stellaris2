# 軽量なPythonベースイメージ
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# 必要なシステムパッケージ (git, ffmpegは必須)
RUN apt-get update && \
    apt-get install -y git ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 依存関係ファイルのコピー
COPY requirements.txt .

# Pythonライブラリのインストール
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY . .

# フォントフォルダ作成
RUN mkdir -p fonts

# 起動コマンド
CMD ["python", "main.py"]
