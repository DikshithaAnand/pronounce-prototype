<h1> Multilingual Pronunciation Learning System (Prototype)</h1>

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

<h2>🗄️ Database Setup (Supabase)</h2>

<p>This project uses Supabase as its database. Follow these steps to configure it:</p>

<h3>1. Create Supabase Project</h3>
<ol>
<li>Go to <a href="https://supabase.com/">Supabase</a> and create a new project.</li>
<li>Navigate to the <strong>SQL Editor</strong> in the left sidebar.</li>
<li>Paste and run the following SQL script to create the necessary tables:</li>
</ol>

<pre>
-- 1. Create Users Table (Optional if using Supabase Auth, but good for custom metadata)
create table public.profiles (
  id uuid references auth.users not null primary key,
  username text unique,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. Create Attempts Table (Stores each recording session)
create table public.attempts (
  id uuid default gen_random_uuid() primary key,
  user_name text not null, -- Stores the user UUID or Name
  passage_text text not null,
  audio_url text,
  wpm float,
  accuracy_score float,
  fluency_score float,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. Create Attempt Errors Table (Stores granular word-level errors)
create table public.attempt_errors (
  id uuid default gen_random_uuid() primary key,
  attempt_id uuid references public.attempts(id) on delete cascade not null,
  word text not null,
  error_type text not null, -- 'deletion', 'substitution', 'insertion'
  confidence_score float,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 4. Enable Row Level Security (RLS) - Optional but Recommended
alter table public.attempts enable row level security;
alter table public.attempt_errors enable row level security;

-- 5. Create Storage Bucket for Audio
insert into storage.buckets (id, name)
values ('audio-uploads', 'audio-uploads');
</pre>

<h3>2. Configure Environment Variables</h3>
<p>You need to create <strong>two</strong> <code>.env</code> files: one for the backend and one for the frontend.</p>

<h4>Backend (.env)</h4>
<p>Create a file named <code>.env</code> inside the <code>backend/</code> folder:</p>
<pre>
# backend/.env
SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_KEY="your-anon-key-here"
</pre>

<h4>Frontend (.env)</h4>
<p>Create a file named <code>.env</code> inside the <code>frontend/</code> folder (or <code>.streamlit/secrets.toml</code> if deploying):</p>
<pre>
# frontend/.env
API_URL="http://localhost:8000"
</pre>

<hr>

<h2>▶️ Running the Application</h2>

<h3>Start Backend</h3>
<pre>
# From the root directory
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
</pre>

<h3>Start Frontend</h3>
<pre>
# Open a new terminal
cd frontend
streamlit run app.py
</pre>


<h2>📝 License</h2>
<p>MIT License</p>
