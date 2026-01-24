<h1>🗣️ Multilingual Pronunciation Learning System (Prototype)</h1>

<p>
An open-source, offline pronunciation-learning tool for Indian languages, using:
</p>

<ul>
<li><b>Whisper</b> (Speech-to-Text)</li>
<li><b>FastAPI Backend</b></li>
<li><b>Streamlit Frontend</b></li>
<li><b>gTTS</b> for TTS</li>
<li><b>Hybrid Scoring (Text + Pronunciation)</b> — coming soon</li>
</ul>

<hr>

<h2>📋 Prerequisites</h2>

<ol>
<li>
<b>Install Docker Desktop:</b> 
Download and install it from the <a href="https://www.docker.com">official Docker website</a>.
</li>
<li>
<b>Install FFmpeg:</b> Required for audio processing (see the <a href="#-installing-ffmpeg">FFmpeg section</a> below).
</li>
<li>
<b>Python 3.9+:</b> Ensure Python is installed on your local machine.
</li>
</ol>

<hr>

<h2>🚀 Features (Current)</h2>
<ul>
<li>Speech recording/upload</li>
<li>Offline transcription using Whisper</li>
<li>Hindi support</li>
<li>Basic text matching</li>
<li>TTS playback of expected sentence</li>
<li>Streamlit UI</li>
<li>FastAPI backend</li>
</ul>

<h2>📌 Planned Features</h2>
<ul>
<li>Word-level scoring</li>
<li>Pronunciation evaluation (speech embeddings)</li>
<li>Hybrid scoring (text + audio)</li>
<li>Forced alignment with WhisperX</li>
<li>Multi-language support</li>
<li>Improved UI visualization</li>
<li>Latency optimization</li>
</ul>

<hr>

<h2>📂 Project Structure</h2>

<pre>
backend/
  app/
    main.py           → FastAPI server
    transcribe.py     → Whisper transcription
    scoring.py        → text scoring (to be upgraded)
    tts.py            → gTTS output
docker/
    docker-compose.yml → To bring up the database
frontend/
  app.py              → Streamlit UI
postgres/
    db_scripts.sql    → Database scripts
uploads/
requirements.txt
</pre>

<hr>

<h2>🛠️ Installation & Setup Guide</h2>

<h3>1️⃣ Clone the repository</h3>
<pre>
git clone &lt;your-repo-url&gt;
cd pronounce-prototype
</pre>

<h3>2️⃣ Database Setup (Docker)</h3>
<p>Bring up the containerized PostgreSQL DB and PGAdmin tool:</p>
<pre>
cd docker
docker-compose up -d
</pre>
<p>
<b>Accessing the DB:</b> Open PGAdmin at <code>http://localhost:5050</code>. 
Use the credentials defined in your <code>docker-compose.yml</code> to log in and execute the scripts located in <code>postgres/db_scripts.sql</code>.
</p>

<h3>3️⃣ Create and activate virtual environment</h3>

<b>Windows:</b>
<pre>
python -m venv .venv
.\.venv\Scripts\activate
</pre>

<b>Mac/Linux:</b>
<pre>
python3 -m venv .venv
source .venv/bin/activate
</pre>

<h3>4️⃣ Install dependencies</h3>
<pre>
pip install --upgrade pip
pip install -r requirements.txt
</pre>

<hr>

<h2 id="-installing-ffmpeg">🎧 Installing FFmpeg</h2>

<h3>Windows</h3>
<ol>
<li>Download FFmpeg from: <a href="https://www.gyan.dev/ffmpeg/builds/">https://www.gyan.dev/ffmpeg/builds/</a></li>
<li>Extract to: <code>C:\ffmpeg\</code></li>
<li>Add to PATH:
<pre>
C:\ffmpeg\bin
</pre>
</li>
<li>Verify:
<pre>ffmpeg -version</pre></li>
</ol>

<h3>Mac</h3>
<pre>brew install ffmpeg</pre>

<h3>Ubuntu/Linux</h3>
<pre>sudo apt install ffmpeg</pre>

<hr>

<h2>▶️ Running the Application</h2>

<h3>Start Backend</h3>
<pre>
# From the root directory
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
</pre>

<h3>Start Frontend</h3>
<pre>
cd frontend
streamlit run app.py
</pre>

<hr>

<h2>📣 Contributing</h2>
<p>Tasks your team will build next:</p>
<ul>
<li>Hybrid scoring engine</li>
<li>Speech embeddings with Wav2Vec2-XLSR</li>
<li>Multilingual support</li>
<li>Word-level segmentation</li>
<li>Forced alignment improvements</li>
<li>UI visualization</li>
</ul>



<p>Practice attempts and word-level analytics are now persisted to PostgreSQL,
including accuracy, fluency, WPM, and error breakdowns.</p>


<h2>📝 License</h2>
<p>MIT License</p>
