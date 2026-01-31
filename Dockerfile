# Python 3.11 (軽量版) をベースに使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システム依存関係のインストール
# ※ git: 一部のライブラリで必要
# ※ ffmpeg: 音楽再生機能(Voice Cog)に必須
RUN apt-get update && \
    apt-get install -y git ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ライブラリの依存関係ファイルをコピー
COPY requirements.txt .

# Pythonライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# ソースコード全体をコピー
COPY . .

# フォントディレクトリの確認（エラー回避用）
RUN mkdir -p fonts

# Botの起動コマンド
CMD ["python", "main.py"]
